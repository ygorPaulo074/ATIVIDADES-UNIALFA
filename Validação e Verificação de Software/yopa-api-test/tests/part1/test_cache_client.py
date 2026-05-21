"""
Parte 1 — Módulo: src/infrastructure/cache/redis_client.py

ESCOPO
------
CacheClient — wrapper sobre Redis. Armazena contexto, histórico,
scores NLP e dados de agente ephemeral.

INFRAESTRUTURA
--------------
O conftest.py substitui o Redis real por `fakeredis.FakeRedis` via
fixture autouse `patch_env`. Por isso os testes funcionam sem Redis
rodando.

TIPOS DE TESTE
--------------
- integration  : usa fakeredis para validar serialização/round-trip
- fallback     : métodos que dependem de TTL (após expiração → None)
- regression   : B2 / R1-8 (scores após TTL → None, sem raise)
                 B9 (is_ephemeral_agent identifica corretamente)
"""
from datetime import datetime, timezone

import pytest

from tests.shared.log_helper import logged

from src.infrastructure.cache.redis_client import CacheClient
from src.domain.conversation import HistoryMessage, ScoreData, SessionMeta


def _msg(content: str, role: str = "user", session_id: str = "s1") -> HistoryMessage:
    return HistoryMessage(
        message_id=f"m-{content[:3]}",
        session_id=session_id,
        role=role,
        content=content,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status="delivered",
    )


@pytest.mark.integration
@pytest.mark.part1
class TestCacheClientContext:
    """Set/get/invalidate do system prompt cacheado por agente."""

    @logged
    def test_set_then_get_context(self):
        cache = CacheClient()
        cache.set_context("agent-1", "Você é um assistente.")
        assert cache.get_context("agent-1") == "Você é um assistente."

    @logged
    def test_get_context_returns_none_when_missing(self):
        cache = CacheClient()
        assert cache.get_context("agent-inexistente") is None

    @logged
    def test_invalidate_context_removes_key(self):
        cache = CacheClient()
        cache.set_context("agent-1", "prompt")
        cache.invalidate_context("agent-1")
        assert cache.get_context("agent-1") is None


@pytest.mark.integration
@pytest.mark.part1
class TestCacheClientHistory:
    """Histórico de mensagens em Redis (lista append-only com TTL)."""

    @logged
    def test_append_then_get_history_roundtrip(self):
        cache = CacheClient()
        msg = _msg("olá")
        cache.append_message("s1", msg)
        history = cache.get_history("s1")
        assert len(history) == 1
        assert history[0].content == "olá"
        assert history[0].role == "user"

    @logged
    def test_get_history_empty_when_no_messages(self):
        cache = CacheClient()
        assert cache.get_history("sessao-vazia") == []

    @logged
    def test_history_preserves_order(self):
        cache = CacheClient()
        cache.append_message("s2", _msg("primeira", session_id="s2"))
        cache.append_message("s2", _msg("segunda", session_id="s2"))
        cache.append_message("s2", _msg("terceira", session_id="s2"))
        history = cache.get_history("s2")
        assert [m.content for m in history] == ["primeira", "segunda", "terceira"]

    @logged
    def test_history_has_ttl(self):
        """Após append_message, a chave deve ter TTL > 0."""
        cache = CacheClient()
        cache.append_message("s3", _msg("x", session_id="s3"))
        ttl = cache._redis.ttl("session:s3:history")
        assert ttl > 0


@pytest.mark.integration
@pytest.mark.part1
class TestCacheClientScores:
    """Persistência de scores NLP por sessão."""

    def _scores(self, session_id: str = "s1") -> ScoreData:
        return ScoreData(
            session_id=session_id,
            avg_sentiment_score=0.5,
            sentiment_label="positive",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    @logged
    def test_set_then_get_scores_roundtrip(self):
        cache = CacheClient()
        scores = self._scores("s1")
        cache.set_scores("s1", scores)
        loaded = cache.get_scores("s1")
        assert loaded is not None
        assert loaded.session_id == "s1"
        assert loaded.avg_sentiment_score == 0.5

    @logged
    def test_scores_have_ttl(self):
        cache = CacheClient()
        cache.set_scores("s4", self._scores("s4"))
        ttl = cache._redis.ttl("session:s4:scores")
        assert ttl > 0


@pytest.mark.integration
@pytest.mark.fallback
@pytest.mark.regression
@pytest.mark.part1
class TestCacheClientScoresExpired:
    """
    Regressão B2 / R1-8: get_scores após expiração retorna None — SEM
    levantar exceção. A rota de insights usa esse None para cair no driver.
    """

    @logged
    def test_get_scores_returns_none_after_manual_delete(self):
        """Simulamos TTL via delete direto da chave (fakeredis suporta TTL real)."""
        cache = CacheClient()
        cache.set_scores("s5", ScoreData(
            session_id="s5",
            updated_at=datetime.now(timezone.utc).isoformat(),
        ))
        cache._redis.delete("session:s5:scores")  # simula expiração
        assert cache.get_scores("s5") is None


@pytest.mark.integration
@pytest.mark.part1
class TestCacheClientSessionMeta:
    """Metadata da sessão (tokens, modelo, started_at, ...)."""

    @logged
    def test_set_then_get_session_meta(self):
        cache = CacheClient()
        meta = SessionMeta(
            session_id="s1",
            agent_id="a1",
            model="gpt-4o",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        cache.set_session_meta("s1", meta)
        loaded = cache.get_session_meta("s1")
        assert loaded is not None
        assert loaded.agent_id == "a1"
        assert loaded.model == "gpt-4o"


@pytest.mark.integration
@pytest.mark.regression
@pytest.mark.part1
class TestCacheClientEphemeralAgent:
    """
    Regressão B9: is_ephemeral_agent identifica agente Redis-only para
    evitar FK violation em writes posteriores no DB.
    """

    @logged
    def test_set_ephemeral_then_get(self):
        cache = CacheClient()
        cache.set_ephemeral_agent(
            agent_id="eph-1",
            name="Test Ephemeral",
            secret_hash="h",
            system_prompt="prompt",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        data = cache.get_ephemeral_agent("eph-1")
        assert data is not None
        assert data["name"] == "Test Ephemeral"

    @logged
    def test_is_ephemeral_true_for_ephemeral_agent(self):
        cache = CacheClient()
        cache.set_ephemeral_agent(
            agent_id="eph-2",
            name="x",
            secret_hash="h",
            system_prompt="p",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        assert cache.is_ephemeral_agent("eph-2") is True

    @logged
    def test_is_ephemeral_false_for_regular_agent(self):
        cache = CacheClient()
        assert cache.is_ephemeral_agent("agent-normal") is False

    @logged
    def test_add_and_list_ephemeral_sessions(self):
        cache = CacheClient()
        cache.add_ephemeral_session("eph-3", "sess-a")
        cache.add_ephemeral_session("eph-3", "sess-b")
        sessions = cache.list_ephemeral_sessions("eph-3")
        assert set(sessions) == {"sess-a", "sess-b"}


@pytest.mark.integration
@pytest.mark.part1
class TestCacheClientDeleteSession:
    """delete_session limpa todas as chaves da sessão (history, scores, meta)."""

    @logged
    def test_delete_session_removes_all_keys(self):
        cache = CacheClient()
        cache.append_message("s9", _msg("x", session_id="s9"))
        cache.set_scores("s9", ScoreData(
            session_id="s9",
            updated_at=datetime.now(timezone.utc).isoformat(),
        ))
        cache.delete_session("s9")
        assert cache.get_history("s9") == []
        assert cache.get_scores("s9") is None
