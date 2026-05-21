"""
Response schemas for /data endpoints — analytics, insights, sessions and user context.
None of these models are used for persistence; they are HTTP-only DTOs.
"""
from typing import Literal, Any
from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.http.schemas.chat import ConversationEntry


# ── /data/chat ──────────────────────────────────────────────

class ChatSummary(BaseModel):
    session_id: str
    agent_id: str
    started_at: str
    ended_at: str | None = None
    total_messages: int
    total_tokens: int
    resolved: bool
    escalated: bool


class ChatListResponse(BaseModel):
    total: int
    chats: list[ChatSummary]


class SessionDetail(ChatSummary):
    pass


class ChatDetailResponse(BaseModel):
    session: SessionDetail
    conversation: list[ConversationEntry]


# ── Insights ─────────────────────────────────────────────────

class SentimentPoint(BaseModel):
    message_id: str
    score: float


class SentimentData(BaseModel):
    score: float
    label: Literal["positive", "neutral", "negative"]
    progression: list[SentimentPoint]


class SentimentInsightResponse(BaseModel):
    session_id: str
    sentiment: SentimentData


class TopicsData(BaseModel):
    detected: list[str]
    main_topic: str
    intent: str | None = None


class TopicsInsightResponse(BaseModel):
    session_id: str
    topics: TopicsData


class MetricsData(BaseModel):
    total_messages: int
    total_tokens: int
    avg_user_message_length: float
    avg_response_time_ms: float
    time_to_escalation_seconds: int | None = None
    resolution: Literal["resolved", "escalated", "open"]


class MetricsInsightResponse(BaseModel):
    session_id: str
    metrics: MetricsData


class AIAnalysis(BaseModel):
    key_points: list[str]
    suggested_actions: list[str]
    summary: str


class SuggestionsInsightResponse(BaseModel):
    session_id: str
    generated_at: str
    ai_analysis: AIAnalysis


class AgentContextSnapshot(BaseModel):
    version: int
    tone: str | None = None
    segment: str | None = None


class FullInsightResponse(BaseModel):
    session_id: str
    agent_id: str
    generated_at: str
    sentiment: SentimentData
    topics: TopicsData
    resolution: Literal["resolved", "escalated", "open"]
    metrics: MetricsData
    agent_context: AgentContextSnapshot
    ai_analysis: AIAnalysis


# ── /data/context ─────────────────────────────────────────────

class UserProfile(BaseModel):
    segment: str | None = None
    language: str | None = None
    form_answers: dict[str, Any] | None = None


class UserContextSummary(BaseModel):
    user_id: str
    created_at: str
    updated_at: str
    profile: UserProfile


class UserContextListResponse(BaseModel):
    total: int
    contexts: list[UserContextSummary]


class UserContextResponse(UserContextSummary):
    pass


# ── /data/analytics ───────────────────────────────────────────

class TopicPattern(BaseModel):
    topic: str
    count: int
    resolution_rate: float | None = None


class PeakHour(BaseModel):
    hour: str
    avg_chats: int


class AnalyticsSummary(BaseModel):
    total_chats: int
    total_messages: int
    total_users: int
    avg_messages_per_chat: float
    avg_chat_duration_seconds: float
    avg_response_time_ms: float
    resolution_rate: float
    escalation_rate: float
    total_tokens_used: int
    avg_tokens_per_chat: float


class AnalyticsPatterns(BaseModel):
    most_common_topics: list[TopicPattern]
    most_common_unresolved_topics: list[TopicPattern]
    peak_hours: list[PeakHour]
    peak_days: list[str]
    avg_messages_to_resolution: float
    avg_messages_to_escalation: float


class SentimentDistribution(BaseModel):
    positive: float
    neutral: float
    negative: float


class AnalyticsSentiment(BaseModel):
    avg_score: float
    distribution: SentimentDistribution


class UserSegment(BaseModel):
    segment: str
    total_users: int
    resolution_rate: float


class AnalyticsUsers(BaseModel):
    new_users: int
    returning_users: int
    avg_chats_per_user: float
    segments: list[UserSegment]


class TimelineEntry(BaseModel):
    date: str
    total_chats: int
    resolved: int
    escalated: int
    new_users: int
    total_tokens: int
    avg_response_time_ms: float
    avg_sentiment_score: float


class AnalyticsPeriod(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: str | None = Field(None, alias="from")
    to: str | None = None


class AnalyticsResponse(BaseModel):
    generated_at: str
    period: AnalyticsPeriod
    summary: AnalyticsSummary
    patterns: AnalyticsPatterns
    sentiment: AnalyticsSentiment
    users: AnalyticsUsers
    timeline: list[TimelineEntry]


class AnalyticsSummaryResponse(BaseModel):
    generated_at: str
    period: AnalyticsPeriod
    summary: AnalyticsSummary


class AnalyticsPatternsResponse(BaseModel):
    generated_at: str
    period: AnalyticsPeriod
    patterns: AnalyticsPatterns


class AnalyticsSentimentResponse(BaseModel):
    generated_at: str
    period: AnalyticsPeriod
    sentiment: AnalyticsSentiment


class AnalyticsUsersResponse(BaseModel):
    generated_at: str
    period: AnalyticsPeriod
    users: AnalyticsUsers


class AnalyticsTimelineResponse(BaseModel):
    generated_at: str
    period: AnalyticsPeriod
    timeline: list[TimelineEntry]
