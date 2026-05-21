"""
Conversation domain entities: message history, session metadata and NLP scores.
"""
from typing import Literal
from pydantic import BaseModel


class HistoryMessage(BaseModel):
    message_id: str
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: str
    status: Literal["delivered", "pending", "failed", "escalated"]
    tokens: int | None = None
    response_time_ms: int | None = None


class SessionMeta(BaseModel):
    session_id: str
    agent_id: str
    user_id: str | None = None
    model: str
    started_at: str
    ended_at: str | None = None
    total_messages: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    resolved: bool = False
    escalated: bool = False


class MessageScore(BaseModel):
    message_id: str
    role: Literal["user", "assistant"]
    text_length: int | None = None
    sentiment_score: float | None = None
    sentiment_label: Literal["positive", "neutral", "negative"] | None = None
    topics: list[str] | None = None
    intent: str | None = None


class ScoreData(BaseModel):
    session_id: str
    messages: list[MessageScore] = []
    avg_sentiment_score: float | None = None
    sentiment_label: Literal["positive", "neutral", "negative"] | None = None
    all_topics: list[str] = []
    main_topic: str | None = None
    intent: str | None = None
    avg_user_message_length: float | None = None
    avg_response_time_ms: float = 0.0
    updated_at: str


class SessionRecord(BaseModel):
    session_id: str
    agent_id: str
    user_id: str | None = None
    model: str
    started_at: str
    ended_at: str | None = None
    total_messages: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    resolved: bool = False
    escalated: bool = False
    deleted_at: str | None = None
