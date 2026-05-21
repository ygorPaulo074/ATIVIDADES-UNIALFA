"""
Local per-message quality analysis, no AI token consumption.
Uses pyspellchecker, argostranslate, textblob, spaCy (en_core_web_sm) and TF-IDF.
Called after each POST /chat message — result accumulated in ScoreData and saved to Redis.
"""
from __future__ import annotations

from collections import Counter
from typing import Literal

from langdetect import detect, LangDetectException
from spellchecker import SpellChecker
from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer

from src.domain.conversation import HistoryMessage, MessageScore, ScoreData
from src.infrastructure.config import settings


_nlp = None
_spell_checkers: dict[str, SpellChecker] = {}
_SPELL_SUPPORTED = {"pt", "en", "es", "fr", "de", "it", "ru"}


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def _get_spell_checker(lang: str) -> SpellChecker | None:
    if lang not in _SPELL_SUPPORTED:
        return None
    if lang not in _spell_checkers:
        _spell_checkers[lang] = SpellChecker(language=lang)
    return _spell_checkers[lang]


def _detect_language(text: str) -> str:
    try:
        return detect(text)
    except LangDetectException:
        return "en"


def _correct_spelling(text: str, lang: str) -> str:
    spell = _get_spell_checker(lang)
    if not spell:
        return text
    words = text.split()
    return " ".join(spell.correction(w) or w for w in words)


def _translate_to_english(text: str, from_lang: str) -> str:
    if from_lang == "en":
        return text
    if from_lang not in settings.ANALYZER_LANGUAGES:
        return text
    try:
        from argostranslate import translate
        installed = translate.get_installed_languages()
        src = next((l for l in installed if l.code == from_lang), None)
        tgt = next((l for l in installed if l.code == "en"), None)
        if not src or not tgt:
            return text
        return src.get_translation(tgt).translate(text)
    except Exception:
        return text


def _classify_sentiment(score: float, threshold: float) -> Literal["positive", "neutral", "negative"]:
    if score < -threshold:
        return "negative"
    if score > threshold:
        return "positive"
    return "neutral"


def _extract_topics(text: str) -> list[str]:
    doc = _get_nlp()(text)
    topics = set()
    for chunk in doc.noun_chunks:
        if len(chunk) >= 2 and not chunk.root.is_stop:
            topics.add(chunk.text.lower().strip())
    return list(topics)


def _extract_intent(text: str) -> str | None:
    doc = _get_nlp()(text)
    for token in doc:
        if token.pos_ == "VERB" and not token.is_stop:
            for child in token.children:
                if child.dep_ == "dobj":
                    return f"{token.lemma_} {child.text}".lower()
    for token in doc:
        if token.pos_ == "VERB" and not token.is_stop:
            return token.lemma_.lower()
    return None


def _compute_main_topic(messages: list[MessageScore]) -> str | None:
    documents = [" ".join(m.topics) for m in messages if m.topics]
    if not documents:
        return None
    if len(documents) == 1:
        return documents[0]
    try:
        vectorizer = TfidfVectorizer()
        matrix = vectorizer.fit_transform(documents)
        scores = matrix.sum(axis=0).A1
        feature_names = vectorizer.get_feature_names_out()
        return feature_names[scores.argmax()]
    except Exception:
        words = [w for doc in documents for w in doc.split()]
        return Counter(words).most_common(1)[0][0] if words else None


def detect_dominant_language(messages: list[HistoryMessage]) -> str | None:
    user_texts = [m.content for m in messages if m.role == "user" and m.content.strip()]
    if not user_texts:
        return None
    langs = [_detect_language(t) for t in user_texts]
    return Counter(langs).most_common(1)[0][0] if langs else None


def preprocess_message(text: str) -> str:
    """Correct spelling. Used before sending to AI to improve comprehension."""
    lang = _detect_language(text)
    return _correct_spelling(text, lang)


def analyze(
    message_id: str,
    role: Literal["user", "assistant"],
    text: str,
    sentiment_threshold: float = 0.3,
) -> MessageScore:
    lang = _detect_language(text)
    corrected = _correct_spelling(text, lang)
    english = _translate_to_english(corrected, lang)

    score = round(TextBlob(english).sentiment.polarity, 4)
    label = _classify_sentiment(score, sentiment_threshold)
    topics = _extract_topics(english) or None
    intent = _extract_intent(english)

    return MessageScore(
        message_id=message_id,
        role=role,
        text_length=len(text),
        sentiment_score=score,
        sentiment_label=label,
        topics=topics,
        intent=intent,
    )


def update_session_scores(
    session_id: str,
    existing: ScoreData | None,
    new_message: MessageScore,
    updated_at: str,
    sentiment_threshold: float = 0.3,
) -> ScoreData:
    messages = (existing.messages if existing else []) + [new_message]
    user_messages = [m for m in messages if m.role == "user"]

    scores = [m.sentiment_score for m in user_messages if m.sentiment_score is not None]
    avg_score = round(sum(scores) / len(scores), 4) if scores else None
    avg_label = _classify_sentiment(avg_score, sentiment_threshold) if avg_score is not None else None

    all_topics = list({t for m in messages for t in (m.topics or [])})
    main_topic = _compute_main_topic(messages)

    intents = [m.intent for m in user_messages if m.intent]
    intent = Counter(intents).most_common(1)[0][0] if intents else None

    lengths = [m.text_length for m in user_messages if m.text_length is not None]
    avg_len = round(sum(lengths) / len(lengths), 1) if lengths else None

    return ScoreData(
        session_id=session_id,
        messages=messages,
        avg_sentiment_score=avg_score,
        sentiment_label=avg_label,
        all_topics=all_topics,
        main_topic=main_topic,
        intent=intent,
        avg_user_message_length=avg_len,
        updated_at=updated_at,
    )
