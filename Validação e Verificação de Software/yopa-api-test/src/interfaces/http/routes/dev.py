"""
Development-only routes — active exclusively when RUN_MODE=development.
All requests to /dev/* return 403 in production.

  GET  /agent-test                  — serve the Agent Test UI (chat + sessions + analytics)
  GET  /dev/agents                  — list all agents (id, name, owner, model, validated)
  POST /dev/token/{agent_id}        — rotate agent API key and return new bearer token
  POST /dev/agent/ephemeral         — create ephemeral agent in Redis (no DB, 24h TTL)
  GET  /dev/agent/ephemeral/sessions
  GET  /dev/agent/ephemeral/sessions/{session_id}
  GET  /dev/agent/ephemeral/analytics
"""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from src.application.context_builder import build_system_prompt
from src.application.services.analytics_service import AnalyticsService
from src.domain.agent import AgentContextBase
from src.interfaces.http.auth import authenticate_agent
from src.interfaces.http.schemas.data import (
    AnalyticsResponse,
    ChatDetailResponse,
    ChatListResponse,
    SessionDetail,
)
from src.infrastructure.cache.redis_client import CacheClient
from src.infrastructure.config import settings
from src.infrastructure.persistence.factory import get_driver
from src.infrastructure.security import generate_api_key, hash_api_key

router = APIRouter()

_STATIC = Path(__file__).parents[3] / "static"


def _require_dev() -> None:
    if settings.RUN_MODE != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development mode (RUN_MODE=development).",
        )


def _require_ephemeral(cache: CacheClient, agent_id: str) -> None:
    if not cache.is_ephemeral_agent(agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ephemeral agent not found")


@router.get("/agent-test", include_in_schema=False)
def agent_test_ui():
    _require_dev()
    return FileResponse(_STATIC / "chat.html")

@router.get("/dev/agents")
def list_agents():
    _require_dev()
    agents = get_driver().list_agents()
    return JSONResponse([
        {
            "agent_id":    a.agent_id,
            "name":        a.name,
            "owner":       a.owner,
            "ai_model":    a.ai_model,
            "ai_validated": a.ai_validated,
            "created_at":  a.created_at,
            "active_since": a.active_since,
            "last_activity_at": a.last_activity_at,
        }
        for a in agents
    ])


@router.post("/dev/token/{agent_id}")
def rotate_token(agent_id: str):
    _require_dev()
    driver = get_driver()
    agent = driver.load_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    new_secret = generate_api_key()
    new_hash = hash_api_key(new_secret)
    now = datetime.now(timezone.utc).isoformat()
    driver.save_agent(agent.model_copy(update={
        "api_key_hash": new_hash,
        "updated_at": now,
    }))

    return JSONResponse({"bearer_token": f"{agent_id}.{new_secret}"})


class EphemeralAgentRequest(BaseModel):
    name: str
    context: dict


@router.post("/dev/agent/ephemeral")
def create_ephemeral_agent(body: EphemeralAgentRequest):
    _require_dev()
    import uuid
    agent_id    = str(uuid.uuid4())
    secret      = generate_api_key()
    secret_hash = hash_api_key(secret)
    context     = AgentContextBase(**body.context)
    system_prompt = build_system_prompt(context)
    now = datetime.now(timezone.utc).isoformat()
    CacheClient().set_ephemeral_agent(
        agent_id,
        body.name,
        secret_hash,
        system_prompt,
        ai_model=settings.AI_MODEL or None,
        created_at=now,
    )
    return JSONResponse({
        "agent_id": agent_id,
        "name":     body.name,
        "api_key":  f"{agent_id}.{secret}",
    })


@router.get("/dev/agent/ephemeral/sessions", response_model=ChatListResponse)
def list_ephemeral_sessions(agent_id: str = Depends(authenticate_agent)):
    _require_dev()
    cache = CacheClient()
    _require_ephemeral(cache, agent_id)
    service = AnalyticsService()
    chats = [service.chat_summary(meta) for meta, _, _ in service.ephemeral_records(agent_id)]
    return ChatListResponse(total=len(chats), chats=chats)


@router.get("/dev/agent/ephemeral/sessions/{session_id}")
def get_ephemeral_session(session_id: str, agent_id: str = Depends(authenticate_agent)):
    _require_dev()
    cache = CacheClient()
    _require_ephemeral(cache, agent_id)
    meta = cache.get_session_meta(session_id)
    if not meta or meta.agent_id != agent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    service = AnalyticsService()
    history = cache.get_history(session_id)
    scores = cache.get_scores(session_id)
    detail = ChatDetailResponse(
        session=SessionDetail(**service.chat_summary(meta).model_dump()),
        conversation=service.conversation_from_history(history),
    )
    return JSONResponse({
        **detail.model_dump(mode="json"),
        "sentiment": service.sentiment_from_scores(scores).model_dump(mode="json"),
        "topics": service.topics_from_scores(scores).model_dump(mode="json"),
        "metrics": service.metrics_from_session(meta, scores, history).model_dump(mode="json"),
    })


@router.get("/dev/agent/ephemeral/analytics", response_model=AnalyticsResponse)
def ephemeral_analytics(agent_id: str = Depends(authenticate_agent)):
    _require_dev()
    cache = CacheClient()
    _require_ephemeral(cache, agent_id)
    return AnalyticsService().build_ephemeral_analytics(agent_id)
