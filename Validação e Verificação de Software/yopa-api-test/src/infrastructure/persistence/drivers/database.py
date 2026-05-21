"""
Relational database persistence driver (PostgreSQL 14+).
Requires DATABASE_URL in .env. Complex fields (lists, nested models) are serialised as JSON.
"""
import json
from sqlalchemy import create_engine, text

from src.infrastructure.config import settings
from src.infrastructure.persistence.base import PersistenceDriver
from src.infrastructure.security import sanitize_pii
from src.domain.agent import AgentRecord, AgentContextRecord
from src.domain.conversation import HistoryMessage, SessionRecord, ScoreData
from src.domain.knowledge import KnowledgeFileRecord
from src.domain.analytics import UserContextRecord, InsightRecord


def _dumps(value) -> str:
    return json.dumps(value) if value is not None else None


def _loads(value):
    return json.loads(value) if value is not None else None


class DatabaseDriver(PersistenceDriver):

    def __init__(self):
        self._engine = create_engine(settings.DATABASE_URL)

    # ── Agent ──────────────────────────────────────────────────────────────────

    def save_agent(self, agent: AgentRecord) -> None:
        sanitized = agent.model_copy(update={"name": sanitize_pii(agent.name)})
        d = sanitized.model_dump()
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO agents
                    (agent_id, name, owner, api_key_hash,
                     created_at, updated_at, active_since, last_activity_at,
                     deleted_at, ai_model, ai_api_key, ai_validated)
                VALUES
                    (:agent_id, :name, :owner, :api_key_hash,
                     :created_at, :updated_at, :active_since, :last_activity_at,
                     :deleted_at, :ai_model, :ai_api_key, :ai_validated)
                ON CONFLICT (agent_id) DO UPDATE SET
                    name             = EXCLUDED.name,
                    api_key_hash     = EXCLUDED.api_key_hash,
                    updated_at       = EXCLUDED.updated_at,
                    active_since     = EXCLUDED.active_since,
                    last_activity_at = EXCLUDED.last_activity_at,
                    deleted_at       = EXCLUDED.deleted_at,
                    ai_model         = EXCLUDED.ai_model,
                    ai_api_key       = EXCLUDED.ai_api_key,
                    ai_validated     = EXCLUDED.ai_validated
            """), d)

    def load_agent(self, agent_id: str) -> AgentRecord | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM agents WHERE agent_id = :id AND deleted_at IS NULL"),
                {"id": agent_id},
            ).fetchone()
        if not row:
            return None
        return AgentRecord.model_validate(dict(row._mapping))

    def list_agents(self) -> list[AgentRecord]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM agents WHERE deleted_at IS NULL ORDER BY created_at DESC")
            ).fetchall()
        return [AgentRecord.model_validate(dict(r._mapping)) for r in rows]

    def delete_agent(self, agent_id: str) -> None:
        with self._engine.begin() as conn:
            for table in (
                "insights", "scores", "session_history", "sessions",
                "knowledge_files", "user_contexts", "agent_contexts", "agents",
            ):
                conn.execute(
                    text(f"DELETE FROM {table} WHERE agent_id = :id"),
                    {"id": agent_id},
                )

    def soft_delete_agent(self, agent_id: str, deleted_at: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text("UPDATE agents SET deleted_at = :deleted_at WHERE agent_id = :id"),
                {"deleted_at": deleted_at, "id": agent_id},
            )

    # ── Agent context ──────────────────────────────────────────────────────────

    def save_context(self, record: AgentContextRecord) -> None:
        d = record.model_dump()
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO agent_contexts (agent_id, version, context, changes, updated_at)
                VALUES (:agent_id, :version, :context, :changes, :updated_at)
                ON CONFLICT (agent_id, version) DO UPDATE SET
                    context    = EXCLUDED.context,
                    changes    = EXCLUDED.changes,
                    updated_at = EXCLUDED.updated_at
            """), {**d, "context": _dumps(d["context"]), "changes": _dumps(d["changes"])})

    def load_context(self, agent_id: str) -> AgentContextRecord | None:
        with self._engine.connect() as conn:
            row = conn.execute(text("""
                SELECT * FROM agent_contexts WHERE agent_id = :id ORDER BY version DESC LIMIT 1
            """), {"id": agent_id}).fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["context"] = _loads(d["context"])
        d["changes"] = _loads(d["changes"]) or []
        return AgentContextRecord.model_validate(d)

    def load_context_history(self, agent_id: str) -> list[AgentContextRecord]:
        with self._engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT * FROM agent_contexts WHERE agent_id = :id ORDER BY version DESC
            """), {"id": agent_id}).fetchall()
        records = []
        for row in rows:
            d = dict(row._mapping)
            d["context"] = _loads(d["context"])
            d["changes"] = _loads(d["changes"]) or []
            records.append(AgentContextRecord.model_validate(d))
        return records

    # ── User context ───────────────────────────────────────────────────────────

    def save_user_context(self, record: UserContextRecord) -> None:
        d = record.model_dump()
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO user_contexts
                    (user_id, agent_id, segment, language, form_answers, created_at, updated_at)
                VALUES
                    (:user_id, :agent_id, :segment, :language, :form_answers, :created_at, :updated_at)
                ON CONFLICT (user_id, agent_id) DO UPDATE SET
                    segment      = EXCLUDED.segment,
                    language     = EXCLUDED.language,
                    form_answers = EXCLUDED.form_answers,
                    updated_at   = EXCLUDED.updated_at
            """), {**d, "form_answers": _dumps(d["form_answers"])})

    def load_user_context(self, agent_id: str, user_id: str) -> UserContextRecord | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM user_contexts WHERE agent_id = :agent_id AND user_id = :user_id"),
                {"agent_id": agent_id, "user_id": user_id},
            ).fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["form_answers"] = _loads(d["form_answers"])
        return UserContextRecord.model_validate(d)

    def list_user_contexts(self, agent_id: str) -> list[UserContextRecord]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM user_contexts WHERE agent_id = :id"),
                {"id": agent_id},
            ).fetchall()
        records = []
        for row in rows:
            d = dict(row._mapping)
            d["form_answers"] = _loads(d["form_answers"])
            records.append(UserContextRecord.model_validate(d))
        return records

    def delete_user_context(self, agent_id: str, user_id: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text("DELETE FROM user_contexts WHERE agent_id = :agent_id AND user_id = :user_id"),
                {"agent_id": agent_id, "user_id": user_id},
            )

    # ── Session ────────────────────────────────────────────────────────────────

    def save_session(self, session: SessionRecord) -> None:
        d = session.model_dump()
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO sessions
                    (session_id, agent_id, user_id, model, started_at, ended_at,
                     total_messages, input_tokens, output_tokens, total_tokens,
                     resolved, escalated, deleted_at)
                VALUES
                    (:session_id, :agent_id, :user_id, :model, :started_at, :ended_at,
                     :total_messages, :input_tokens, :output_tokens, :total_tokens,
                     :resolved, :escalated, :deleted_at)
                ON CONFLICT (session_id) DO UPDATE SET
                    ended_at       = EXCLUDED.ended_at,
                    total_messages = EXCLUDED.total_messages,
                    input_tokens   = EXCLUDED.input_tokens,
                    output_tokens  = EXCLUDED.output_tokens,
                    total_tokens   = EXCLUDED.total_tokens,
                    resolved       = EXCLUDED.resolved,
                    escalated      = EXCLUDED.escalated
            """), d)

    def load_session(self, agent_id: str, session_id: str) -> SessionRecord | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM sessions WHERE agent_id = :agent_id AND session_id = :session_id AND deleted_at IS NULL"),
                {"agent_id": agent_id, "session_id": session_id},
            ).fetchone()
        if not row:
            return None
        return SessionRecord.model_validate(dict(row._mapping))

    def list_sessions(self, agent_id: str) -> list[SessionRecord]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM sessions WHERE agent_id = :id AND deleted_at IS NULL"),
                {"id": agent_id},
            ).fetchall()
        return [SessionRecord.model_validate(dict(row._mapping)) for row in rows]

    def delete_session(self, agent_id: str, session_id: str) -> None:
        with self._engine.begin() as conn:
            for table in ("insights", "scores", "sessions"):
                conn.execute(
                    text(f"DELETE FROM {table} WHERE agent_id = :agent_id AND session_id = :session_id"),
                    {"agent_id": agent_id, "session_id": session_id},
                )

    def soft_delete_session(self, agent_id: str, session_id: str, deleted_at: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text("UPDATE sessions SET deleted_at = :deleted_at WHERE agent_id = :agent_id AND session_id = :session_id"),
                {"deleted_at": deleted_at, "agent_id": agent_id, "session_id": session_id},
            )

    # ── Session history ────────────────────────────────────────────────────────

    def save_history(self, agent_id: str, session_id: str, messages: list[HistoryMessage]) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO session_history (session_id, agent_id, messages)
                VALUES (:session_id, :agent_id, :messages)
                ON CONFLICT (session_id) DO UPDATE SET messages = EXCLUDED.messages
            """), {
                "session_id": session_id,
                "agent_id": agent_id,
                "messages": _dumps([m.model_dump() for m in messages]),
            })

    def load_history(self, agent_id: str, session_id: str) -> list[HistoryMessage]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT messages FROM session_history WHERE agent_id = :agent_id AND session_id = :session_id"),
                {"agent_id": agent_id, "session_id": session_id},
            ).fetchone()
        if not row:
            return []
        return [HistoryMessage.model_validate(m) for m in (_loads(row.messages) or [])]

    # ── Scores ─────────────────────────────────────────────────────────────────

    def save_scores(self, agent_id: str, scores: ScoreData) -> None:
        d = scores.model_dump()
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO scores
                    (session_id, agent_id, messages, avg_sentiment_score, sentiment_label,
                     all_topics, main_topic, intent, avg_user_message_length,
                     avg_response_time_ms, updated_at)
                VALUES
                    (:session_id, :agent_id, :messages, :avg_sentiment_score, :sentiment_label,
                     :all_topics, :main_topic, :intent, :avg_user_message_length,
                     :avg_response_time_ms, :updated_at)
                ON CONFLICT (session_id) DO UPDATE SET
                    messages                = EXCLUDED.messages,
                    avg_sentiment_score     = EXCLUDED.avg_sentiment_score,
                    sentiment_label         = EXCLUDED.sentiment_label,
                    all_topics              = EXCLUDED.all_topics,
                    main_topic              = EXCLUDED.main_topic,
                    intent                  = EXCLUDED.intent,
                    avg_user_message_length = EXCLUDED.avg_user_message_length,
                    avg_response_time_ms    = EXCLUDED.avg_response_time_ms,
                    updated_at              = EXCLUDED.updated_at
            """), {
                **d,
                "agent_id": agent_id,
                "messages": _dumps(d["messages"]),
                "all_topics": _dumps(d["all_topics"]),
            })

    def load_scores(self, agent_id: str, session_id: str) -> ScoreData | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM scores WHERE agent_id = :agent_id AND session_id = :session_id"),
                {"agent_id": agent_id, "session_id": session_id},
            ).fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["messages"] = _loads(d["messages"]) or []
        d["all_topics"] = _loads(d["all_topics"]) or []
        return ScoreData.model_validate(d)

    def load_all_scores(self, agent_id: str) -> list[ScoreData]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM scores WHERE agent_id = :agent_id"),
                {"agent_id": agent_id},
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row._mapping)
            d["messages"] = _loads(d["messages"]) or []
            d["all_topics"] = _loads(d["all_topics"]) or []
            result.append(ScoreData.model_validate(d))
        return result

    # ── Insights ───────────────────────────────────────────────────────────────

    def save_insight(self, agent_id: str, insight: InsightRecord) -> None:
        d = insight.model_dump()
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO insights
                    (session_id, agent_id, generated_at, key_points, suggested_actions, summary)
                VALUES
                    (:session_id, :agent_id, :generated_at, :key_points, :suggested_actions, :summary)
                ON CONFLICT (session_id) DO UPDATE SET
                    generated_at      = EXCLUDED.generated_at,
                    key_points        = EXCLUDED.key_points,
                    suggested_actions = EXCLUDED.suggested_actions,
                    summary           = EXCLUDED.summary
            """), {
                **d,
                "agent_id": agent_id,
                "key_points": _dumps(d["key_points"]),
                "suggested_actions": _dumps(d["suggested_actions"]),
            })

    def load_insight(self, agent_id: str, session_id: str) -> InsightRecord | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM insights WHERE agent_id = :agent_id AND session_id = :session_id"),
                {"agent_id": agent_id, "session_id": session_id},
            ).fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["key_points"] = _loads(d["key_points"]) or []
        d["suggested_actions"] = _loads(d["suggested_actions"]) or []
        return InsightRecord.model_validate(d)

    # ── Knowledge files ────────────────────────────────────────────────────────

    def save_knowledge_file(self, agent_id: str, record: KnowledgeFileRecord) -> None:
        d = record.model_dump()
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO knowledge_files
                    (file_id, agent_id, filename, file_type, records, uploaded_at, updated_at)
                VALUES
                    (:file_id, :agent_id, :filename, :file_type, :records, :uploaded_at, :updated_at)
                ON CONFLICT (file_id) DO UPDATE SET
                    filename   = EXCLUDED.filename,
                    file_type  = EXCLUDED.file_type,
                    records    = EXCLUDED.records,
                    updated_at = EXCLUDED.updated_at
            """), {**d, "records": _dumps(d["records"])})

    def load_knowledge_file(self, agent_id: str, file_id: str) -> KnowledgeFileRecord | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM knowledge_files WHERE agent_id = :agent_id AND file_id = :file_id"),
                {"agent_id": agent_id, "file_id": file_id},
            ).fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["records"] = _loads(d["records"]) or []
        return KnowledgeFileRecord.model_validate(d)

    def list_knowledge_files(self, agent_id: str) -> list[KnowledgeFileRecord]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM knowledge_files WHERE agent_id = :id"),
                {"id": agent_id},
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row._mapping)
            d["records"] = _loads(d["records"]) or []
            result.append(KnowledgeFileRecord.model_validate(d))
        return result

    def delete_knowledge_file(self, agent_id: str, file_id: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text("DELETE FROM knowledge_files WHERE agent_id = :agent_id AND file_id = :file_id"),
                {"agent_id": agent_id, "file_id": file_id},
            )

    # ── Soft delete purge ──────────────────────────────────────────────────────

    def purge_deleted(self, before: str) -> dict:
        with self._engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM agents WHERE deleted_at IS NOT NULL AND deleted_at < :before"),
                {"before": before},
            )
            agents_purged = result.rowcount
            result = conn.execute(
                text("DELETE FROM sessions WHERE deleted_at IS NOT NULL AND deleted_at < :before"),
                {"before": before},
            )
            sessions_purged = result.rowcount
        return {"agents_purged": agents_purged, "sessions_purged": sessions_purged}
