"""
Parte 1 — Módulo: src/infrastructure/persistence/

ESCOPO
------
Validar que o driver Local respeita o contrato `PersistenceDriver` (ABC)
para todas as entidades: agent, context, session, history, scores,
insights, knowledge_files, user_context, e o purge_deleted.

NOTAS
-----
O conftest aponta `settings.DATA_PATH` para tmp_path em cada teste, então
os arquivos JSON ficam isolados por execução.

TIPOS DE TESTE
--------------
- integration  : todos
- regression   : B5 / R1-10 — soft delete + purge_deleted
"""
from datetime import datetime, timezone, timedelta

import pytest

from tests.shared.log_helper import logged

from src.infrastructure.persistence.drivers.local import LocalDriver
from src.domain.agent import AgentRecord, AgentContextBase, AgentContextRecord
from src.domain.conversation import (
    HistoryMessage, SessionRecord, ScoreData, MessageScore,
)
from src.domain.knowledge import KnowledgeFileRecord
from src.domain.analytics import UserContextRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _agent(agent_id: str = "a1", name: str = "Agente Teste") -> AgentRecord:
    return AgentRecord(
        agent_id=agent_id,
        name=name,
        owner="dono",
        api_key_hash="hash",
        created_at=_now(),
        updated_at=_now(),
    )


def _ctx_record(agent_id: str = "a1", version: int = 1, persona: str = "Persona") -> AgentContextRecord:
    return AgentContextRecord(
        agent_id=agent_id,
        version=version,
        context=AgentContextBase(persona=persona, language="pt"),
        updated_at=_now(),
    )


def _msg(session_id: str, role: str = "user", content: str = "oi") -> HistoryMessage:
    return HistoryMessage(
        message_id=f"m-{role}-{content[:3]}",
        session_id=session_id,
        role=role,
        content=content,
        timestamp=_now(),
        status="delivered",
    )


@pytest.mark.integration
@pytest.mark.part1
class TestAgentRoundtrip:
    """save_agent + load_agent — driver Local."""

    @logged
    def test_save_then_load_agent(self):
        d = LocalDriver()
        d.save_agent(_agent("a1"))
        loaded = d.load_agent("a1")
        assert loaded is not None
        assert loaded.agent_id == "a1"

    @logged
    def test_load_nonexistent_returns_none(self):
        d = LocalDriver()
        assert d.load_agent("nao-existe") is None

    @logged
    def test_list_agents_returns_saved_records(self):
        d = LocalDriver()
        d.save_agent(_agent("a1", "Um"))
        d.save_agent(_agent("a2", "Dois"))
        agents = d.list_agents()
        ids = {a.agent_id for a in agents}
        assert ids == {"a1", "a2"}


@pytest.mark.integration
@pytest.mark.part1
class TestContextHistory:
    """Versionamento de contexto."""

    @logged
    def test_save_creates_current(self):
        d = LocalDriver()
        d.save_context(_ctx_record("a1", version=1, persona="P1"))
        current = d.load_context("a1")
        assert current is not None
        assert current.version == 1
        assert current.context.persona == "P1"

    @logged
    def test_save_v2_keeps_v1_in_history(self):
        d = LocalDriver()
        d.save_context(_ctx_record("a1", version=1, persona="P1"))
        d.save_context(_ctx_record("a1", version=2, persona="P2"))
        history = d.load_context_history("a1")
        versions = [r.version for r in history]
        assert 1 in versions
        assert 2 in versions

    @logged
    def test_load_context_returns_latest_saved(self):
        d = LocalDriver()
        d.save_context(_ctx_record("a1", version=1, persona="P1"))
        d.save_context(_ctx_record("a1", version=2, persona="P2"))
        latest = d.load_context("a1")
        assert latest.context.persona == "P2"
        assert latest.version == 2

    @logged
    def test_history_sorted_by_version_desc(self):
        d = LocalDriver()
        d.save_context(_ctx_record("a1", version=1))
        d.save_context(_ctx_record("a1", version=2))
        d.save_context(_ctx_record("a1", version=3))
        history = d.load_context_history("a1")
        assert [r.version for r in history] == [3, 2, 1]


@pytest.mark.integration
@pytest.mark.regression
@pytest.mark.part1
class TestSoftDeleteAndPurge:
    """
    Regressão B5 / R1-10:
    - soft_delete marca deleted_at
    - load_agent NÃO retorna agente soft-deleted (filtra)
    - purge_deleted(before) remove permanentemente quem tem
      deleted_at < before
    """

    @logged
    def test_soft_delete_marks_deleted_at(self):
        d = LocalDriver()
        d.save_agent(_agent("a1"))
        d.soft_delete_agent("a1", deleted_at=_now())
        # load_agent filtra registros com deleted_at, devolve None
        assert d.load_agent("a1") is None

    @logged
    def test_purge_removes_old_soft_deleted_records(self):
        d = LocalDriver()
        d.save_agent(_agent("a1"))
        # marca como deletado 10 dias atrás
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        d.soft_delete_agent("a1", deleted_at=old)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        result = d.purge_deleted(before=cutoff)
        assert result["agents_purged"] >= 1

    @logged
    def test_purge_keeps_recent_soft_deleted_records(self):
        d = LocalDriver()
        d.save_agent(_agent("a2"))
        recent = _now()  # acabou de deletar
        d.soft_delete_agent("a2", deleted_at=recent)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        result = d.purge_deleted(before=cutoff)
        # registro recente não deve ser purgado
        assert result["agents_purged"] == 0


@pytest.mark.integration
@pytest.mark.part1
class TestSessionScoresHistoryRoundtrip:
    """Persistência de session/scores/history — a tríade do _persist_snapshot."""

    @logged
    def test_save_session_then_load_session(self):
        d = LocalDriver()
        sess = SessionRecord(
            session_id="s1", agent_id="a1", model="gpt-4o",
            started_at=_now(),
        )
        d.save_session(sess)
        loaded = d.load_session("a1", "s1")
        assert loaded is not None
        assert loaded.session_id == "s1"

    @logged
    def test_save_scores_then_load_scores(self):
        d = LocalDriver()
        sc = ScoreData(session_id="s1", updated_at=_now())
        d.save_scores("a1", sc)
        loaded = d.load_scores("a1", "s1")
        assert loaded is not None
        assert loaded.session_id == "s1"

    @logged
    def test_save_history_then_load_history(self):
        d = LocalDriver()
        messages = [_msg("s1", role="user", content="oi"),
                    _msg("s1", role="assistant", content="ola")]
        d.save_history("a1", "s1", messages)
        loaded = d.load_history("a1", "s1")
        assert len(loaded) == 2
        assert loaded[0].content == "oi"
        assert loaded[1].content == "ola"

    @logged
    def test_load_all_scores_returns_all_sessions(self):
        d = LocalDriver()
        d.save_session(SessionRecord(session_id="s1", agent_id="a1", model="x", started_at=_now()))
        d.save_session(SessionRecord(session_id="s2", agent_id="a1", model="x", started_at=_now()))
        d.save_scores("a1", ScoreData(session_id="s1", updated_at=_now()))
        d.save_scores("a1", ScoreData(session_id="s2", updated_at=_now()))
        all_scores = d.load_all_scores("a1")
        sids = {s.session_id for s in all_scores}
        assert sids == {"s1", "s2"}


@pytest.mark.integration
@pytest.mark.part1
class TestKnowledgeFilesRoundtrip:
    """save/load/list/delete de knowledge files."""

    @logged
    def test_save_then_load_knowledge_file(self):
        d = LocalDriver()
        kf = KnowledgeFileRecord(
            file_id="f1", agent_id="a1", filename="x.csv",
            file_type="csv", records=[{"k": "v"}],
            uploaded_at=_now(), updated_at=_now(),
        )
        d.save_knowledge_file("a1", kf)
        loaded = d.load_knowledge_file("a1", "f1")
        assert loaded is not None
        assert loaded.filename == "x.csv"

    @logged
    def test_list_returns_all_files(self):
        d = LocalDriver()
        for i in range(3):
            d.save_knowledge_file("a1", KnowledgeFileRecord(
                file_id=f"f{i}", agent_id="a1", filename=f"x{i}.csv",
                file_type="csv", uploaded_at=_now(), updated_at=_now(),
            ))
        assert len(d.list_knowledge_files("a1")) == 3

    @logged
    def test_delete_removes_file(self):
        d = LocalDriver()
        d.save_knowledge_file("a1", KnowledgeFileRecord(
            file_id="f1", agent_id="a1", filename="x.csv",
            file_type="csv", uploaded_at=_now(), updated_at=_now(),
        ))
        d.delete_knowledge_file("a1", "f1")
        assert d.load_knowledge_file("a1", "f1") is None
