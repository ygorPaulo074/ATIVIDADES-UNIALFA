"""
Local filesystem persistence driver.
Stores agents, sessions and scores as JSON files under DATA_PATH.

Directory layout:
  {DATA_PATH}/agents/{agent_id}/agent.json
  {DATA_PATH}/agents/{agent_id}/context/current.json
  {DATA_PATH}/agents/{agent_id}/context/history/v{n}.json
  {DATA_PATH}/agents/{agent_id}/users/{user_id}.json
  {DATA_PATH}/agents/{agent_id}/chats/{session_id}/session.json
  {DATA_PATH}/agents/{agent_id}/chats/{session_id}/scores.json
  {DATA_PATH}/agents/{agent_id}/chats/{session_id}/insights.json
"""
import json
import shutil
from pathlib import Path

from src.infrastructure.config import settings
from src.infrastructure.persistence.base import PersistenceDriver
from src.infrastructure.security import sanitize_pii
from src.domain.agent import AgentRecord, AgentContextRecord
from src.domain.conversation import HistoryMessage, SessionRecord, ScoreData
from src.domain.knowledge import KnowledgeFileRecord
from src.domain.analytics import UserContextRecord, InsightRecord


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class LocalDriver(PersistenceDriver):

    def __init__(self):
        self._base = Path(settings.DATA_PATH)

    # ── Path helpers ───────────────────────────────────────────────────────────

    def _agent_dir(self, agent_id: str) -> Path:
        return self._base / "agents" / agent_id

    def _agent_file(self, agent_id: str) -> Path:
        return self._agent_dir(agent_id) / "agent.json"

    def _context_current(self, agent_id: str) -> Path:
        return self._agent_dir(agent_id) / "context" / "current.json"

    def _context_version(self, agent_id: str, version: int) -> Path:
        return self._agent_dir(agent_id) / "context" / "history" / f"v{version}.json"

    def _context_history_dir(self, agent_id: str) -> Path:
        return self._agent_dir(agent_id) / "context" / "history"

    def _user_file(self, agent_id: str, user_id: str) -> Path:
        return self._agent_dir(agent_id) / "users" / f"{user_id}.json"

    def _users_dir(self, agent_id: str) -> Path:
        return self._agent_dir(agent_id) / "users"

    def _session_file(self, agent_id: str, session_id: str) -> Path:
        return self._agent_dir(agent_id) / "chats" / session_id / "session.json"

    def _chats_dir(self, agent_id: str) -> Path:
        return self._agent_dir(agent_id) / "chats"

    def _scores_file(self, agent_id: str, session_id: str) -> Path:
        return self._agent_dir(agent_id) / "chats" / session_id / "scores.json"

    def _insights_file(self, agent_id: str, session_id: str) -> Path:
        return self._agent_dir(agent_id) / "chats" / session_id / "insights.json"

    def _history_file(self, agent_id: str, session_id: str) -> Path:
        return self._agent_dir(agent_id) / "chats" / session_id / "history.json"

    def _knowledge_file(self, agent_id: str, file_id: str) -> Path:
        return self._agent_dir(agent_id) / "knowledge" / f"{file_id}.json"

    def _knowledge_dir(self, agent_id: str) -> Path:
        return self._agent_dir(agent_id) / "knowledge"

    # ── Agent ──────────────────────────────────────────────────────────────────

    def save_agent(self, agent: AgentRecord) -> None:
        sanitized = agent.model_copy(update={"name": sanitize_pii(agent.name)})
        _write(self._agent_file(agent.agent_id), sanitized.model_dump(mode="json"))

    def load_agent(self, agent_id: str) -> AgentRecord | None:
        data = _read(self._agent_file(agent_id))
        if not data:
            return None
        record = AgentRecord.model_validate(data)
        return None if record.deleted_at else record

    def list_agents(self) -> list[AgentRecord]:
        agents_dir = self._base / "agents"
        if not agents_dir.exists():
            return []
        result = []
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir():
                data = _read(agent_dir / "agent.json")
                if data:
                    record = AgentRecord.model_validate(data)
                    if not record.deleted_at:
                        result.append(record)
        return sorted(result, key=lambda r: r.created_at, reverse=True)

    def delete_agent(self, agent_id: str) -> None:
        agent_dir = self._agent_dir(agent_id)
        if agent_dir.exists():
            shutil.rmtree(agent_dir)

    def soft_delete_agent(self, agent_id: str, deleted_at: str) -> None:
        data = _read(self._agent_file(agent_id))
        if data:
            data["deleted_at"] = deleted_at
            _write(self._agent_file(agent_id), data)

    # ── Agent context ──────────────────────────────────────────────────────────

    def save_context(self, record: AgentContextRecord) -> None:
        data = record.model_dump(mode="json")
        _write(self._context_current(record.agent_id), data)
        _write(self._context_version(record.agent_id, record.version), data)

    def load_context(self, agent_id: str) -> AgentContextRecord | None:
        data = _read(self._context_current(agent_id))
        return AgentContextRecord.model_validate(data) if data else None

    def load_context_history(self, agent_id: str) -> list[AgentContextRecord]:
        history_dir = self._context_history_dir(agent_id)
        if not history_dir.exists():
            return []
        records = []
        for file in history_dir.glob("v*.json"):
            data = _read(file)
            if data:
                records.append(AgentContextRecord.model_validate(data))
        return sorted(records, key=lambda r: r.version, reverse=True)

    # ── User context ───────────────────────────────────────────────────────────

    def save_user_context(self, record: UserContextRecord) -> None:
        _write(self._user_file(record.agent_id, record.user_id), record.model_dump(mode="json"))

    def load_user_context(self, agent_id: str, user_id: str) -> UserContextRecord | None:
        data = _read(self._user_file(agent_id, user_id))
        return UserContextRecord.model_validate(data) if data else None

    def list_user_contexts(self, agent_id: str) -> list[UserContextRecord]:
        users_dir = self._users_dir(agent_id)
        if not users_dir.exists():
            return []
        records = []
        for file in users_dir.glob("*.json"):
            data = _read(file)
            if data:
                records.append(UserContextRecord.model_validate(data))
        return records

    def delete_user_context(self, agent_id: str, user_id: str) -> None:
        path = self._user_file(agent_id, user_id)
        if path.exists():
            path.unlink()

    # ── Session ────────────────────────────────────────────────────────────────

    def save_session(self, session: SessionRecord) -> None:
        _write(self._session_file(session.agent_id, session.session_id), session.model_dump(mode="json"))

    def load_session(self, agent_id: str, session_id: str) -> SessionRecord | None:
        data = _read(self._session_file(agent_id, session_id))
        if not data:
            return None
        record = SessionRecord.model_validate(data)
        return None if record.deleted_at else record

    def list_sessions(self, agent_id: str) -> list[SessionRecord]:
        chats_dir = self._chats_dir(agent_id)
        if not chats_dir.exists():
            return []
        records = []
        for session_dir in chats_dir.iterdir():
            if session_dir.is_dir():
                data = _read(session_dir / "session.json")
                if data:
                    record = SessionRecord.model_validate(data)
                    if not record.deleted_at:
                        records.append(record)
        return records

    def delete_session(self, agent_id: str, session_id: str) -> None:
        session_dir = self._agent_dir(agent_id) / "chats" / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)

    def soft_delete_session(self, agent_id: str, session_id: str, deleted_at: str) -> None:
        path = self._session_file(agent_id, session_id)
        data = _read(path)
        if data:
            data["deleted_at"] = deleted_at
            _write(path, data)

    # ── Session history ────────────────────────────────────────────────────────

    def save_history(self, agent_id: str, session_id: str, messages: list[HistoryMessage]) -> None:
        _write(self._history_file(agent_id, session_id), {"messages": [m.model_dump(mode="json") for m in messages]})

    def load_history(self, agent_id: str, session_id: str) -> list[HistoryMessage]:
        data = _read(self._history_file(agent_id, session_id))
        if not data:
            return []
        return [HistoryMessage.model_validate(m) for m in data.get("messages", [])]

    # ── Scores ─────────────────────────────────────────────────────────────────

    def save_scores(self, agent_id: str, scores: ScoreData) -> None:
        _write(self._scores_file(agent_id, scores.session_id), scores.model_dump(mode="json"))

    def load_scores(self, agent_id: str, session_id: str) -> ScoreData | None:
        data = _read(self._scores_file(agent_id, session_id))
        return ScoreData.model_validate(data) if data else None

    def load_all_scores(self, agent_id: str) -> list[ScoreData]:
        chats_dir = self._chats_dir(agent_id)
        if not chats_dir.exists():
            return []
        result = []
        for session_dir in chats_dir.iterdir():
            if session_dir.is_dir():
                data = _read(session_dir / "scores.json")
                if data:
                    result.append(ScoreData.model_validate(data))
        return result

    # ── Insights ───────────────────────────────────────────────────────────────

    def save_insight(self, agent_id: str, insight: InsightRecord) -> None:
        _write(self._insights_file(agent_id, insight.session_id), insight.model_dump(mode="json"))

    def load_insight(self, agent_id: str, session_id: str) -> InsightRecord | None:
        data = _read(self._insights_file(agent_id, session_id))
        return InsightRecord.model_validate(data) if data else None

    # ── Knowledge files ────────────────────────────────────────────────────────

    def save_knowledge_file(self, agent_id: str, record: KnowledgeFileRecord) -> None:
        _write(self._knowledge_file(agent_id, record.file_id), record.model_dump(mode="json"))

    def load_knowledge_file(self, agent_id: str, file_id: str) -> KnowledgeFileRecord | None:
        data = _read(self._knowledge_file(agent_id, file_id))
        return KnowledgeFileRecord.model_validate(data) if data else None

    def list_knowledge_files(self, agent_id: str) -> list[KnowledgeFileRecord]:
        d = self._knowledge_dir(agent_id)
        if not d.exists():
            return []
        records = []
        for path in d.glob("*.json"):
            data = _read(path)
            if data:
                records.append(KnowledgeFileRecord.model_validate(data))
        return records

    def delete_knowledge_file(self, agent_id: str, file_id: str) -> None:
        path = self._knowledge_file(agent_id, file_id)
        if path.exists():
            path.unlink()

    # ── Soft delete purge ──────────────────────────────────────────────────────

    def purge_deleted(self, before: str) -> dict:
        agents_dir = self._base / "agents"
        agents_purged = 0
        sessions_purged = 0
        if not agents_dir.exists():
            return {"agents_purged": 0, "sessions_purged": 0}

        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            agent_file = agent_dir / "agent.json"
            data = _read(agent_file)
            if data and data.get("deleted_at") and data["deleted_at"] < before:
                shutil.rmtree(agent_dir)
                agents_purged += 1
                continue

            chats_dir = agent_dir / "chats"
            if not chats_dir.exists():
                continue
            for session_dir in chats_dir.iterdir():
                if not session_dir.is_dir():
                    continue
                session_data = _read(session_dir / "session.json")
                if session_data and session_data.get("deleted_at") and session_data["deleted_at"] < before:
                    shutil.rmtree(session_dir)
                    sessions_purged += 1

        return {"agents_purged": agents_purged, "sessions_purged": sessions_purged}
