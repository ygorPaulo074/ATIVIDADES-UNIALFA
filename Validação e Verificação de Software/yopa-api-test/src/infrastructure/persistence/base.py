"""
Abstract contract for persistence drivers (Strategy Pattern).
All persistence calls in services must operate against this contract,
never against a concrete driver directly — allows swapping storage via .env
without changing business logic.
PII sanitisation and security are the responsibility of the concrete drivers.
"""
from abc import ABC, abstractmethod

from src.domain.agent import AgentRecord, AgentContextRecord
from src.domain.conversation import HistoryMessage, SessionRecord, ScoreData
from src.domain.knowledge import KnowledgeFileRecord
from src.domain.analytics import UserContextRecord, InsightRecord


class PersistenceDriver(ABC):

    # ── Agent ──────────────────────────────────────────────────────────────────

    @abstractmethod
    def save_agent(self, agent: AgentRecord) -> None: ...

    @abstractmethod
    def load_agent(self, agent_id: str) -> AgentRecord | None: ...

    @abstractmethod
    def list_agents(self) -> list[AgentRecord]: ...

    @abstractmethod
    def delete_agent(self, agent_id: str) -> None: ...

    @abstractmethod
    def soft_delete_agent(self, agent_id: str, deleted_at: str) -> None: ...

    # ── Agent context ──────────────────────────────────────────────────────────

    @abstractmethod
    def save_context(self, record: AgentContextRecord) -> None: ...

    @abstractmethod
    def load_context(self, agent_id: str) -> AgentContextRecord | None: ...

    @abstractmethod
    def load_context_history(self, agent_id: str) -> list[AgentContextRecord]: ...

    # ── User context ───────────────────────────────────────────────────────────

    @abstractmethod
    def save_user_context(self, record: UserContextRecord) -> None: ...

    @abstractmethod
    def load_user_context(self, agent_id: str, user_id: str) -> UserContextRecord | None: ...

    @abstractmethod
    def list_user_contexts(self, agent_id: str) -> list[UserContextRecord]: ...

    @abstractmethod
    def delete_user_context(self, agent_id: str, user_id: str) -> None: ...

    # ── Session ────────────────────────────────────────────────────────────────

    @abstractmethod
    def save_session(self, session: SessionRecord) -> None: ...

    @abstractmethod
    def load_session(self, agent_id: str, session_id: str) -> SessionRecord | None: ...

    @abstractmethod
    def list_sessions(self, agent_id: str) -> list[SessionRecord]: ...

    @abstractmethod
    def delete_session(self, agent_id: str, session_id: str) -> None: ...

    @abstractmethod
    def soft_delete_session(self, agent_id: str, session_id: str, deleted_at: str) -> None: ...

    # ── Session history ────────────────────────────────────────────────────────

    @abstractmethod
    def save_history(self, agent_id: str, session_id: str, messages: list[HistoryMessage]) -> None: ...

    @abstractmethod
    def load_history(self, agent_id: str, session_id: str) -> list[HistoryMessage]: ...

    # ── Scores ─────────────────────────────────────────────────────────────────

    @abstractmethod
    def save_scores(self, agent_id: str, scores: ScoreData) -> None: ...

    @abstractmethod
    def load_scores(self, agent_id: str, session_id: str) -> ScoreData | None: ...

    @abstractmethod
    def load_all_scores(self, agent_id: str) -> list[ScoreData]: ...

    # ── Insights ───────────────────────────────────────────────────────────────

    @abstractmethod
    def save_insight(self, agent_id: str, insight: InsightRecord) -> None: ...

    @abstractmethod
    def load_insight(self, agent_id: str, session_id: str) -> InsightRecord | None: ...

    # ── Knowledge files ────────────────────────────────────────────────────────

    @abstractmethod
    def save_knowledge_file(self, agent_id: str, record: KnowledgeFileRecord) -> None: ...

    @abstractmethod
    def load_knowledge_file(self, agent_id: str, file_id: str) -> KnowledgeFileRecord | None: ...

    @abstractmethod
    def list_knowledge_files(self, agent_id: str) -> list[KnowledgeFileRecord]: ...

    @abstractmethod
    def delete_knowledge_file(self, agent_id: str, file_id: str) -> None: ...

    # ── Soft delete purge ──────────────────────────────────────────────────────

    @abstractmethod
    def purge_deleted(self, before: str) -> dict: ...
