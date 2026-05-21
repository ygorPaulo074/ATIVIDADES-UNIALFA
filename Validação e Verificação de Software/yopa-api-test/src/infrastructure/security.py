"""
Utilitários de segurança: sanitização de PII, geração e verificação de API Keys,
e criptografia de secrets (Fernet) para conexões SQL e credenciais de IA por agente.
Chamado por drivers de persistência e services — nunca diretamente por routes.
"""
import hmac
import secrets
import hashlib
from typing import cast

from loguru import logger
from cryptography.fernet import Fernet, InvalidToken
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities.engine.recognizer_result import RecognizerResult as AnonymizerRecognizerResult


_nlp_config = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "pt", "model_name": "pt_core_news_sm"}],
}
_analyzer = AnalyzerEngine(
    nlp_engine=NlpEngineProvider(nlp_configuration=_nlp_config).create_engine(),
    supported_languages=["pt", "en"],
)
_anonymizer = AnonymizerEngine()


def sanitize_pii(text: str) -> str:
    if not text or not text.strip():
        return text
    try:
        results = cast(list[AnonymizerRecognizerResult], _analyzer.analyze(text=text, language="pt"))
        if not results:
            return text
        anonymized = _anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized.text
    except Exception as exc:
        logger.warning(f"sanitize_pii failed, text returned without sanitisation: {exc}")
        return text


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(key: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_api_key(key), stored_hash)


# ── Credential encryption ──────────────────────────────────────────────────────

_ENC_PREFIX = "enc:"
_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance
    from src.infrastructure.config import settings
    key = settings.SQL_ENCRYPTION_KEY
    if not key:
        logger.warning("SQL_ENCRYPTION_KEY not set — using an ephemeral key (non-persistent).")
        key = Fernet.generate_key().decode()
    _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet_instance


def encrypt_secret(plaintext: str) -> str:
    if plaintext.startswith(_ENC_PREFIX):
        return plaintext
    token = _get_fernet().encrypt(plaintext.encode()).decode()
    return f"{_ENC_PREFIX}{token}"


def decrypt_secret(ciphertext: str) -> str:
    if not ciphertext.startswith(_ENC_PREFIX):
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext[len(_ENC_PREFIX):].encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt credential — invalid key or corrupted data.") from exc


def mask_connection_string(conn_str: str) -> str:
    if conn_str.startswith(_ENC_PREFIX):
        return "[encrypted]"
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(conn_str)
        if parsed.password:
            netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
            return urlunparse(parsed._replace(netloc=netloc))
    except Exception:
        pass
    return conn_str
