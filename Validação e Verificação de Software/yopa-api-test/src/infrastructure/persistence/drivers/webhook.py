"""
Unidirectional HTTP persistence driver.
Dispatches each write operation as a POST to WEBHOOK_URL from .env.
Read operations (load_*, list_*) raise NotImplementedError.
"""
import requests

from src.infrastructure.config import settings
from src.infrastructure.persistence.base import PersistenceDriver
from src.infrastructure.security import sanitize_pii
from src.domain.agent import AgentRecord, AgentContextRecord
from src.domain.conversation import HistoryMessage, SessionRecord, ScoreData
from src.domain.knowledge import KnowledgeFileRecord
from src.domain.analytics import UserContextRecord, InsightRecord


class WebhookDriver(PersistenceDriver):

    def _post(self, payload: dict) -> None:
        requests.post(settings.WEBHOOK_URL, json=payload, timeout=10)

    # ── Agent ──────────────────────────────────────────────────────────────────

    def save_agent(self, agent: AgentRecord) -> None:
        sanitized = agent.model_copy(update={"name": sanitize_pii(agent.name)})
        self._post({"type": "agent", "action": "save", "data": sanitized.model_dump()})

    def load_agent(self, agent_id: str) -> AgentRecord | None:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    def list_agents(self) -> list[AgentRecord]:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    def delete_agent(self, agent_id: str) -> None:
        self._post({"type": "agent", "action": "delete", "agent_id": agent_id})

    def soft_delete_agent(self, agent_id: str, deleted_at: str) -> None:
        self._post({"type": "agent", "action": "soft_delete", "agent_id": agent_id, "deleted_at": deleted_at})

    # ── Agent context ──────────────────────────────────────────────────────────

    def save_context(self, record: AgentContextRecord) -> None:
        self._post({"type": "agent_context", "action": "save", "data": record.model_dump()})

    def load_context(self, agent_id: str) -> AgentContextRecord | None:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    def load_context_history(self, agent_id: str) -> list[AgentContextRecord]:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    # ── User context ───────────────────────────────────────────────────────────

    def save_user_context(self, record: UserContextRecord) -> None:
        self._post({"type": "user_context", "action": "save", "data": record.model_dump()})

    def load_user_context(self, agent_id: str, user_id: str) -> UserContextRecord | None:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    def list_user_contexts(self, agent_id: str) -> list[UserContextRecord]:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    def delete_user_context(self, agent_id: str, user_id: str) -> None:
        self._post({"type": "user_context", "action": "delete", "agent_id": agent_id, "user_id": user_id})

    # ── Session ────────────────────────────────────────────────────────────────

    def save_session(self, session: SessionRecord) -> None:
        self._post({"type": "session", "action": "save", "data": session.model_dump()})

    def load_session(self, agent_id: str, session_id: str) -> SessionRecord | None:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    def list_sessions(self, agent_id: str) -> list[SessionRecord]:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    def delete_session(self, agent_id: str, session_id: str) -> None:
        self._post({"type": "session", "action": "delete", "agent_id": agent_id, "session_id": session_id})

    def soft_delete_session(self, agent_id: str, session_id: str, deleted_at: str) -> None:
        self._post({"type": "session", "action": "soft_delete",
                    "agent_id": agent_id, "session_id": session_id, "deleted_at": deleted_at})

    # ── Session history ────────────────────────────────────────────────────────

    def save_history(self, agent_id: str, session_id: str, messages: list[HistoryMessage]) -> None:
        self._post({"type": "history", "action": "save", "agent_id": agent_id, "session_id": session_id,
                    "data": [m.model_dump() for m in messages]})

    def load_history(self, agent_id: str, session_id: str) -> list[HistoryMessage]:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    # ── Scores ─────────────────────────────────────────────────────────────────

    def save_scores(self, agent_id: str, scores: ScoreData) -> None:
        self._post({"type": "scores", "action": "save", "agent_id": agent_id, "data": scores.model_dump()})

    def load_scores(self, agent_id: str, session_id: str) -> ScoreData | None:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    def load_all_scores(self, agent_id: str) -> list[ScoreData]:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    # ── Insights ───────────────────────────────────────────────────────────────

    def save_insight(self, agent_id: str, insight: InsightRecord) -> None:
        self._post({"type": "insight", "action": "save", "agent_id": agent_id, "data": insight.model_dump()})

    def load_insight(self, agent_id: str, session_id: str) -> InsightRecord | None:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    # ── Knowledge files ────────────────────────────────────────────────────────

    def save_knowledge_file(self, agent_id: str, record: KnowledgeFileRecord) -> None:
        self._post({"type": "knowledge_file", "action": "save", "agent_id": agent_id,
                    "data": record.model_dump(mode="json")})

    def load_knowledge_file(self, agent_id: str, file_id: str) -> KnowledgeFileRecord | None:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    def list_knowledge_files(self, agent_id: str) -> list[KnowledgeFileRecord]:
        raise NotImplementedError("WebhookDriver não suporta leitura.")

    def delete_knowledge_file(self, agent_id: str, file_id: str) -> None:
        self._post({"type": "knowledge_file", "action": "delete",
                    "agent_id": agent_id, "file_id": file_id})

    # ── Soft delete purge ──────────────────────────────────────────────────────

    def purge_deleted(self, before: str) -> dict:
        raise NotImplementedError("WebhookDriver não suporta purge.")
