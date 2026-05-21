"""
Manages the agent lifecycle.
Depends on PersistenceDriver (via factory) for storage,
CacheClient for context invalidation and ContextService for versioning.
"""
import secrets
import uuid
from datetime import datetime, timezone

from src.infrastructure.persistence.factory import get_driver
from src.infrastructure.persistence.base import PersistenceDriver
from src.infrastructure.cache.redis_client import CacheClient
from src.infrastructure.security import hash_api_key, encrypt_secret
from src.domain.agent import AgentContextBase, AgentRecord
from src.domain.conversation import SessionRecord
from src.application.services.context_service import ContextService


class AgentService:

    def __init__(self):
        self.driver: PersistenceDriver = get_driver()
        self.cache = CacheClient()
        self.context_service = ContextService()

    def create_agent(
        self,
        name: str,
        owner: str,
        context: AgentContextBase,
        ai_model: str | None = None,
        ai_api_key: str | None = None,
    ) -> dict:
        agent_id = str(uuid.uuid4())
        secret = secrets.token_urlsafe(32)
        raw_key = f"{agent_id}.{secret}"
        now = datetime.now(timezone.utc).isoformat()
        record = AgentRecord(
            agent_id=agent_id,
            name=name,
            owner=owner,
            api_key_hash=hash_api_key(secret),
            created_at=now,
            updated_at=now,
            ai_model=ai_model,
            ai_api_key=encrypt_secret(ai_api_key) if ai_api_key else None,
        )
        self.driver.save_agent(record)
        self.context_service.create_context(agent_id, context)
        return {"agent_id": agent_id, "api_key": raw_key, "created_at": now}

    def get_agent(self, agent_id: str) -> AgentRecord | None:
        return self.driver.load_agent(agent_id)

    def patch_agent(self, agent_id: str, name: str) -> AgentRecord:
        record = self.driver.load_agent(agent_id)
        if not record:
            raise ValueError("Agent not found")
        now = datetime.now(timezone.utc).isoformat()
        updated = record.model_copy(update={"name": name, "updated_at": now})
        self.driver.save_agent(updated)
        return updated

    def get_metrics(self, agent_id: str) -> dict:
        sessions: list[SessionRecord] = self.driver.list_sessions(agent_id)
        total = len(sessions)
        if total == 0:
            return {
                "total_sessions": 0,
                "total_messages": 0,
                "total_tokens": 0,
                "resolution_rate": 0.0,
                "escalation_rate": 0.0,
            }
        total_messages = sum(s.total_messages for s in sessions)
        total_tokens = sum(s.total_tokens for s in sessions)
        resolved = sum(1 for s in sessions if s.resolved)
        escalated = sum(1 for s in sessions if s.escalated)
        return {
            "total_sessions": total,
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "resolution_rate": round(resolved / total, 4),
            "escalation_rate": round(escalated / total, 4),
        }

    def delete_agent(self, agent_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.driver.soft_delete_agent(agent_id, now)
        self.cache.invalidate_context(agent_id)
