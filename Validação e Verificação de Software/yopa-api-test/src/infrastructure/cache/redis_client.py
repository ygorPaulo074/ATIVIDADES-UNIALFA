"""
Redis cache layer.
Centralises access to agent context, session history, NLP scores and metadata.
Agent context has no fixed TTL — it is explicitly invalidated on PUT /agent/context.
Sessions use SESSION_TTL renewed on every message.
"""
from redis import ConnectionPool, Redis
from redis.exceptions import RedisError

from src.infrastructure.config import settings
from src.domain.conversation import HistoryMessage, SessionMeta, ScoreData


_pools: dict[str, ConnectionPool] = {}


def _get_pool(url: str) -> ConnectionPool:
    if url not in _pools:
        _pools[url] = ConnectionPool.from_url(url, decode_responses=True)
    return _pools[url]


def _context_key(agent_id: str) -> str:
    return f"agent:{agent_id}:context"

def _history_key(session_id: str) -> str:
    return f"session:{session_id}:history"

def _scores_key(session_id: str) -> str:
    return f"session:{session_id}:scores"

def _meta_key(session_id: str) -> str:
    return f"session:{session_id}:meta"

def _ephemeral_sessions_key(agent_id: str) -> str:
    return f"agent:{agent_id}:ephemeral:sessions"


class CacheClient:

    def __init__(self):
        self._redis = Redis(connection_pool=_get_pool(settings.REDIS_URL))

    def ping(self) -> bool:
        try:
            return bool(self._redis.ping())
        except RedisError:
            return False

    # ── Agent context ──────────────────────────────────────────

    def get_context(self, agent_id: str) -> str | None:
        return self._redis.get(_context_key(agent_id))

    def set_context(self, agent_id: str, system_prompt: str) -> None:
        self._redis.set(_context_key(agent_id), system_prompt)

    def invalidate_context(self, agent_id: str) -> None:
        self._redis.delete(_context_key(agent_id))

    # ── Session history ────────────────────────────────────────

    def get_history(self, session_id: str) -> list[HistoryMessage]:
        raw = self._redis.lrange(_history_key(session_id), 0, -1)
        return [HistoryMessage.model_validate_json(item) for item in raw]

    def append_message(self, session_id: str, message: HistoryMessage, ttl: int = 0) -> None:
        resolved_ttl = ttl or settings.SESSION_TTL
        key = _history_key(session_id)
        with self._redis.pipeline() as pipe:
            pipe.rpush(key, message.model_dump_json())
            pipe.expire(key, resolved_ttl)
            pipe.execute()

    # ── NLP scores ─────────────────────────────────────────────

    def get_scores(self, session_id: str) -> ScoreData | None:
        raw = self._redis.get(_scores_key(session_id))
        return ScoreData.model_validate_json(raw) if raw else None

    def set_scores(self, session_id: str, scores: ScoreData) -> None:
        self._redis.set(_scores_key(session_id), scores.model_dump_json(), ex=settings.SESSION_TTL)

    # ── Session metadata ───────────────────────────────────────

    def get_session_meta(self, session_id: str) -> SessionMeta | None:
        raw = self._redis.get(_meta_key(session_id))
        return SessionMeta.model_validate_json(raw) if raw else None

    def set_session_meta(self, session_id: str, meta: SessionMeta, ttl: int = 0) -> None:
        resolved_ttl = ttl or settings.SESSION_TTL
        self._redis.set(_meta_key(session_id), meta.model_dump_json(), ex=resolved_ttl)

    # ── Ephemeral agents (dev only) ───────────────────────────

    def set_ephemeral_agent(
        self,
        agent_id: str,
        name: str,
        secret_hash: str,
        system_prompt: str,
        *,
        owner: str = "ephemeral",
        ai_model: str | None = None,
        created_at: str,
        ttl: int = 86400,
    ) -> None:
        key = f"agent:{agent_id}:ephemeral"
        mapping = {
            "name": name,
            "secret_hash": secret_hash,
            "owner": owner,
            "created_at": created_at,
            "updated_at": created_at,
            "active_since": created_at,
        }
        if ai_model:
            mapping["ai_model"] = ai_model
        self._redis.hset(key, mapping=mapping)
        self._redis.expire(key, ttl)
        self.set_context(agent_id, system_prompt)

    def get_ephemeral_agent(self, agent_id: str) -> dict | None:
        data = self._redis.hgetall(f"agent:{agent_id}:ephemeral")
        return data if data else None

    def is_ephemeral_agent(self, agent_id: str) -> bool:
        return bool(self._redis.exists(f"agent:{agent_id}:ephemeral"))

    def add_ephemeral_session(self, agent_id: str, session_id: str, ttl: int = 86400) -> None:
        key = _ephemeral_sessions_key(agent_id)
        with self._redis.pipeline() as pipe:
            pipe.sadd(key, session_id)
            pipe.expire(key, ttl)
            pipe.execute()

    def list_ephemeral_sessions(self, agent_id: str) -> list[str]:
        return sorted(self._redis.smembers(_ephemeral_sessions_key(agent_id)))

    # ── Cleanup ────────────────────────────────────────────────

    def delete_session(self, session_id: str) -> None:
        self._redis.delete(
            _history_key(session_id),
            _scores_key(session_id),
            _meta_key(session_id),
        )
