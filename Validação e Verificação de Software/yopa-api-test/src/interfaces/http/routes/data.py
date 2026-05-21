"""
Endpoints de dados e analytics.
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.services.analytics_service import AnalyticsService
from src.interfaces.http.auth import authenticate_agent
from src.infrastructure.cache.redis_client import CacheClient
from src.infrastructure.persistence.factory import get_driver
from src.domain.analytics import InsightRecord
from src.domain.conversation import HistoryMessage
from src.infrastructure.config import settings
from src.infrastructure.ai.client import AIClient
from src.interfaces.http.schemas.data import (
    ChatListResponse,
    ChatDetailResponse, SessionDetail,
    SentimentInsightResponse,
    TopicsInsightResponse,
    MetricsInsightResponse,
    SuggestionsInsightResponse, AIAnalysis,
    FullInsightResponse, AgentContextSnapshot,
    UserContextListResponse, UserContextSummary, UserProfile, UserContextResponse,
    AnalyticsResponse, AnalyticsSummaryResponse, AnalyticsPatternsResponse,
    AnalyticsSentimentResponse, AnalyticsUsersResponse, AnalyticsTimelineResponse,
)

router = APIRouter(prefix="/data", tags=["data"])


# ── /data/chat ─────────────────────────────────────────────────────────────────

@router.get("/chat", response_model=ChatListResponse)
def list_chats(agent_id: str = Depends(authenticate_agent)):
    sessions = get_driver().list_sessions(agent_id)
    service = AnalyticsService()
    chats = [service.chat_summary(s) for s in sessions]
    return ChatListResponse(total=len(chats), chats=chats)


@router.get("/chat/{session_id}", response_model=ChatDetailResponse)
def get_chat(session_id: str, agent_id: str = Depends(authenticate_agent)):
    driver = get_driver()
    session = driver.load_session(agent_id, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    history = CacheClient().get_history(session_id)
    if not history:
        history = driver.load_history(agent_id, session_id)
    service = AnalyticsService()
    return ChatDetailResponse(
        session=SessionDetail(**service.chat_summary(session).model_dump()),
        conversation=service.conversation_from_history(history),
    )


@router.delete("/chat/{session_id}", status_code=204)
def delete_chat(session_id: str, agent_id: str = Depends(authenticate_agent)):
    driver = get_driver()
    session = driver.load_session(agent_id, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    now = datetime.now(timezone.utc).isoformat()
    driver.soft_delete_session(agent_id, session_id, now)
    CacheClient().delete_session(session_id)


# ── Insights ───────────────────────────────────────────────────────────────────

def _require_scores(agent_id: str, session_id: str):
    scores = CacheClient().get_scores(session_id)
    if not scores:
        scores = get_driver().load_scores(agent_id, session_id)
    if not scores:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No analysis data for this session")
    return scores


def _require_session(agent_id: str, session_id: str):
    session = get_driver().load_session(agent_id, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.get("/chat/{session_id}/insights/sentiment", response_model=SentimentInsightResponse)
def insight_sentiment(session_id: str, agent_id: str = Depends(authenticate_agent)):
    _require_session(agent_id, session_id)
    scores = _require_scores(agent_id, session_id)
    return SentimentInsightResponse(
        session_id=session_id,
        sentiment=AnalyticsService().sentiment_from_scores(scores),
    )


@router.get("/chat/{session_id}/insights/topics", response_model=TopicsInsightResponse)
def insight_topics(session_id: str, agent_id: str = Depends(authenticate_agent)):
    _require_session(agent_id, session_id)
    scores = _require_scores(agent_id, session_id)
    return TopicsInsightResponse(
        session_id=session_id,
        topics=AnalyticsService().topics_from_scores(scores),
    )


@router.get("/chat/{session_id}/insights/metrics", response_model=MetricsInsightResponse)
def insight_metrics(session_id: str, agent_id: str = Depends(authenticate_agent)):
    session = _require_session(agent_id, session_id)
    scores = CacheClient().get_scores(session_id)
    history = CacheClient().get_history(session_id)

    return MetricsInsightResponse(
        session_id=session_id,
        metrics=AnalyticsService().metrics_from_session(session, scores, history),
    )


def _call_ai_for_insight(history_text: str) -> dict:
    msg = HistoryMessage(
        message_id="0",
        session_id="0",
        role="user",
        content=(
            f"Analyze the following chat transcript and respond in JSON only.\n\n"
            f"Transcript:\n{history_text}\n\n"
            'Return exactly: {"key_points": ["..."], "suggested_actions": ["..."], "summary": "..."}'
        ),
        timestamp="",
        status="delivered",
    )
    response = AIClient().complete(
        system="You are an AI assistant that analyzes chat conversations and returns structured JSON insights.",
        messages=[msg],
        max_tokens=512,
    )
    try:
        start = response.content.find("{")
        end = response.content.rfind("}") + 1
        return json.loads(response.content[start:end])
    except Exception:
        return {"key_points": [], "suggested_actions": [], "summary": response.content}


@router.get("/chat/{session_id}/insights/suggestions", response_model=SuggestionsInsightResponse)
def insight_suggestions(session_id: str, agent_id: str = Depends(authenticate_agent)):
    _require_session(agent_id, session_id)
    history = CacheClient().get_history(session_id)
    history_text = "\n".join(f"{m.role.upper()}: {m.content}" for m in history)
    ai_data = _call_ai_for_insight(history_text)
    now = datetime.now(timezone.utc).isoformat()
    return SuggestionsInsightResponse(
        session_id=session_id,
        generated_at=now,
        ai_analysis=AIAnalysis(**ai_data),
    )


@router.get("/chat/{session_id}/insights", response_model=FullInsightResponse)
def insight_full(session_id: str, agent_id: str = Depends(authenticate_agent)):
    session = _require_session(agent_id, session_id)
    scores = _require_scores(agent_id, session_id)
    history = CacheClient().get_history(session_id)
    history_text = "\n".join(f"{m.role.upper()}: {m.content}" for m in history)
    ai_data = _call_ai_for_insight(history_text)
    now = datetime.now(timezone.utc).isoformat()

    service = AnalyticsService()

    context_record = None
    try:
        from src.application.services.context_service import ContextService
        rec = ContextService().load_context(agent_id)
        if rec:
            context_record = AgentContextSnapshot(
                version=rec.version,
                tone=rec.context.tone,
                segment=rec.context.segment,
            )
    except Exception:
        pass

    insight = InsightRecord(
        session_id=session_id,
        generated_at=now,
        key_points=ai_data.get("key_points", []),
        suggested_actions=ai_data.get("suggested_actions", []),
        summary=ai_data.get("summary", ""),
    )
    get_driver().save_insight(agent_id, insight)

    return FullInsightResponse(
        session_id=session_id,
        agent_id=agent_id,
        generated_at=now,
        sentiment=service.sentiment_from_scores(scores),
        topics=service.topics_from_scores(scores),
        resolution=service.resolution(session),
        metrics=service.metrics_from_session(session, scores, history),
        agent_context=context_record,
        ai_analysis=AIAnalysis(**ai_data),
    )


# ── /data/context ──────────────────────────────────────────────────────────────

@router.get("/context", response_model=UserContextListResponse)
def list_contexts(agent_id: str = Depends(authenticate_agent)):
    records = get_driver().list_user_contexts(agent_id)
    contexts = [
        UserContextSummary(
            user_id=r.user_id,
            created_at=r.created_at,
            updated_at=r.updated_at,
            profile=UserProfile(segment=r.segment, language=r.language, form_answers=r.form_answers),
        )
        for r in records
    ]
    return UserContextListResponse(total=len(contexts), contexts=contexts)


@router.get("/context/{user_id}", response_model=UserContextResponse)
def get_context(user_id: str, agent_id: str = Depends(authenticate_agent)):
    record = get_driver().load_user_context(agent_id, user_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User context not found")
    return UserContextResponse(
        user_id=record.user_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
        profile=UserProfile(segment=record.segment, language=record.language, form_answers=record.form_answers),
    )


@router.delete("/context/{user_id}", status_code=204)
def delete_context(user_id: str, agent_id: str = Depends(authenticate_agent)):
    record = get_driver().load_user_context(agent_id, user_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User context not found")
    get_driver().delete_user_context(agent_id, user_id)


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics_full(
    agent_id: str = Depends(authenticate_agent),
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
):
    return AnalyticsService().build_persistent_analytics(agent_id, from_, to)


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
def analytics_summary(
    agent_id: str = Depends(authenticate_agent),
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
):
    data = AnalyticsService().build_persistent_analytics(agent_id, from_, to)
    return AnalyticsSummaryResponse(generated_at=data.generated_at, period=data.period, summary=data.summary)


@router.get("/analytics/patterns", response_model=AnalyticsPatternsResponse)
def analytics_patterns(
    agent_id: str = Depends(authenticate_agent),
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
):
    data = AnalyticsService().build_persistent_analytics(agent_id, from_, to)
    return AnalyticsPatternsResponse(generated_at=data.generated_at, period=data.period, patterns=data.patterns)


@router.get("/analytics/sentiment", response_model=AnalyticsSentimentResponse)
def analytics_sentiment(
    agent_id: str = Depends(authenticate_agent),
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
):
    data = AnalyticsService().build_persistent_analytics(agent_id, from_, to)
    return AnalyticsSentimentResponse(generated_at=data.generated_at, period=data.period, sentiment=data.sentiment)


@router.get("/analytics/users", response_model=AnalyticsUsersResponse)
def analytics_users(
    agent_id: str = Depends(authenticate_agent),
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
):
    data = AnalyticsService().build_persistent_analytics(agent_id, from_, to)
    return AnalyticsUsersResponse(generated_at=data.generated_at, period=data.period, users=data.users)


@router.get("/analytics/timeline", response_model=AnalyticsTimelineResponse)
def analytics_timeline(
    agent_id: str = Depends(authenticate_agent),
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
):
    data = AnalyticsService().build_persistent_analytics(agent_id, from_, to)
    return AnalyticsTimelineResponse(generated_at=data.generated_at, period=data.period, timeline=data.timeline)
