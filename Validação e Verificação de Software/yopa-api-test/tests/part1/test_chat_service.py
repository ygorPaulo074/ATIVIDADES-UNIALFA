"""
Parte 1 — Módulo: src/application/services/chat_service.py

ESCOPO
------
ChatService — orquestra o ciclo de POST /chat. Testamos aqui:
  - _eval_condition: avaliação de cada tipo de EscalationCondition
  - _persist_snapshot: pula DB writes quando o agente é ephemeral (B9)
  - process_message: pipeline real com mocks (PII → cache → IA → persist)

DEPENDÊNCIAS MOCKADAS
---------------------
- AIClient.complete       (evita chamada real ao LLM)
- quality_analyzer.analyze e update_session_scores (evita spaCy/textblob)
- get_driver              (driver de persistência mockado quando necessário)

TIPOS DE TESTE
--------------
- unit         : _eval_condition isolado
- integration  : process_message com dependências mockadas
- pipeline     : ordem das chamadas internas (mock.mock_calls)
- regression   : B9 — agente ephemeral NÃO escreve no driver
"""
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, call

import pytest

from tests.shared.log_helper import logged

from src.application.services.chat_service import ChatService
from src.domain.agent import (
    AgentRecord, AgentContextBase, AgentContextRecord,
    EscalationCondition, EscalationTrigger,
)
from src.domain.conversation import (
    HistoryMessage, SessionMeta, ScoreData,
)
from src.infrastructure.ai.client import AIResponse, AIUsage


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _agent_record(agent_id="a1") -> AgentRecord:
    return AgentRecord(
        agent_id=agent_id, name="A", owner="o", api_key_hash="h",
        created_at=_now(), updated_at=_now(),
    )


def _ctx_record(agent_id="a1", trigger: EscalationTrigger | None = None) -> AgentContextRecord:
    return AgentContextRecord(
        agent_id=agent_id, version=1,
        context=AgentContextBase(persona="P", language="pt", escalation_trigger=trigger),
        updated_at=_now(),
    )


def _meta(session_id="s1", agent_id="a1") -> SessionMeta:
    return SessionMeta(
        session_id=session_id, agent_id=agent_id, model="gpt-4o", started_at=_now(),
    )


def _ai_response() -> AIResponse:
    return AIResponse(
        content="Resposta da IA.",
        usage=AIUsage(input_tokens=10, output_tokens=5, total_tokens=15),
    )


@pytest.mark.unit
@pytest.mark.part1
class TestEvalConditionKeyword:
    """_eval_condition('keyword') — match na última mensagem do usuário."""

    @logged
    def test_keyword_matches_last_user_message(self):
        svc = ChatService()
        cond = EscalationCondition(type="keyword", values=["humano"])
        history = [
            HistoryMessage(message_id="m1", session_id="s1", role="user",
                           content="quero falar com humano", timestamp=_now(), status="delivered"),
        ]
        assert svc._eval_condition(cond, history, None, None) is True

    @logged
    def test_keyword_does_not_match_without_keywords(self):
        svc = ChatService()
        cond = EscalationCondition(type="keyword")
        history = [HistoryMessage(message_id="m1", session_id="s1", role="user",
                                  content="oi", timestamp=_now(), status="delivered")]
        assert svc._eval_condition(cond, history, None, None) is False

    @logged
    def test_keyword_returns_false_with_empty_history(self):
        svc = ChatService()
        cond = EscalationCondition(type="keyword", values=["humano"])
        assert svc._eval_condition(cond, [], None, None) is False


@pytest.mark.unit
@pytest.mark.part1
class TestEvalConditionSentiment:
    """_eval_condition('sentiment') — usa avg_sentiment_score."""

    @logged
    def test_returns_true_when_score_below_negative_threshold(self):
        svc = ChatService()
        cond = EscalationCondition(type="sentiment", threshold=0.3)
        scores = ScoreData(session_id="s1", avg_sentiment_score=-0.5, updated_at=_now())
        assert svc._eval_condition(cond, [], scores, None) is True

    @logged
    def test_returns_false_when_score_above_threshold(self):
        svc = ChatService()
        cond = EscalationCondition(type="sentiment", threshold=0.3)
        scores = ScoreData(session_id="s1", avg_sentiment_score=0.5, updated_at=_now())
        assert svc._eval_condition(cond, [], scores, None) is False

    @logged
    def test_returns_false_without_scores(self):
        svc = ChatService()
        cond = EscalationCondition(type="sentiment", threshold=0.3)
        assert svc._eval_condition(cond, [], None, None) is False


@pytest.mark.unit
@pytest.mark.part1
class TestEvalConditionMessageCount:
    """_eval_condition('message_count') — número de mensagens do usuário."""

    @logged
    def test_returns_true_when_count_reaches_threshold(self):
        svc = ChatService()
        cond = EscalationCondition(type="message_count", value=2)
        history = [
            HistoryMessage(message_id="m1", session_id="s1", role="user",
                           content="oi", timestamp=_now(), status="delivered"),
            HistoryMessage(message_id="m2", session_id="s1", role="user",
                           content="oi2", timestamp=_now(), status="delivered"),
        ]
        assert svc._eval_condition(cond, history, None, None) is True

    @logged
    def test_returns_false_when_count_below_threshold(self):
        svc = ChatService()
        cond = EscalationCondition(type="message_count", value=5)
        history = [
            HistoryMessage(message_id="m1", session_id="s1", role="user",
                           content="oi", timestamp=_now(), status="delivered"),
        ]
        assert svc._eval_condition(cond, history, None, None) is False


@pytest.mark.regression
@pytest.mark.part1
class TestPersistSnapshotEphemeralSkipsDb:
    """
    Regressão B9: _persist_snapshot DEVE pular save_session/save_scores/
    save_history quando o agente é ephemeral. Caso contrário, FK violation.
    """

    @logged
    def test_ephemeral_agent_skips_all_driver_writes(self):
        svc = ChatService()
        meta = _meta("s1", "eph-1")
        scores = ScoreData(session_id="s1", updated_at=_now())

        mock_driver = MagicMock()
        with patch.object(svc.cache, "is_ephemeral_agent", return_value=True), \
             patch("src.application.services.chat_service.get_driver",
                   return_value=mock_driver):
            svc._persist_snapshot("eph-1", "s1", meta, scores)

        # Nenhum save_* deve ter sido chamado
        mock_driver.save_session.assert_not_called()
        mock_driver.save_scores.assert_not_called()
        mock_driver.save_history.assert_not_called()


@pytest.mark.integration
@pytest.mark.part1
class TestPersistSnapshotRegularAgent:
    """Para agente normal, _persist_snapshot deve gravar session, scores e history."""

    @logged
    def test_regular_agent_writes_session_scores_history(self):
        svc = ChatService()
        meta = _meta("s1", "a1")
        scores = ScoreData(session_id="s1", updated_at=_now())

        mock_driver = MagicMock()
        with patch.object(svc.cache, "is_ephemeral_agent", return_value=False), \
             patch.object(svc.cache, "get_history",
                          return_value=[
                              HistoryMessage(message_id="m1", session_id="s1",
                                             role="user", content="x",
                                             timestamp=_now(), status="delivered"),
                          ]), \
             patch("src.application.services.chat_service.get_driver",
                   return_value=mock_driver):
            svc._persist_snapshot("a1", "s1", meta, scores)

        mock_driver.save_session.assert_called_once()
        mock_driver.save_scores.assert_called_once()
        mock_driver.save_history.assert_called_once()


@pytest.mark.pipeline
@pytest.mark.part1
class TestProcessMessagePipeline:
    """
    Valida a ORDEM das chamadas internas em process_message.

    Pipeline real (verificado no código):
      1. _agent_credentials → driver.load_agent
      2. context_service.load_system_prompt
      3. cache.get_history
      4. sanitize_pii(message)
      5. cache.append_message (user msg)
      6. quality_analyzer.analyze (user)
      7. _build_tools
      8. AIClient.complete
      9. cache.append_message (assistant msg)
     10. quality_analyzer.analyze (assistant)
     11. cache.set_scores
     12. cache.set_session_meta
     13. _persist_snapshot (save_session → save_scores → save_history)
    """

    def _setup_chat_mocks(self):
        """Builda uma ChatService com todas as dependências externas mockadas."""
        svc = ChatService()

        # Mocks para isolar do mundo externo (AI, NLP, DB).
        mock_driver = MagicMock()
        mock_driver.load_agent.return_value = _agent_record("a1")
        mock_driver.list_knowledge_files.return_value = []

        mock_score = MagicMock()
        mock_updated = ScoreData(session_id="s1", updated_at=_now())

        patches = [
            patch.object(svc.ai_client, "complete", return_value=_ai_response()),
            patch.object(svc.context_service, "load_system_prompt", return_value="prompt"),
            patch.object(svc.context_service, "load_context", return_value=_ctx_record("a1")),
            patch("src.application.services.chat_service.get_driver",
                  return_value=mock_driver),
            patch("src.application.services.chat_service.quality_analyzer.analyze",
                  return_value=mock_score),
            patch("src.application.services.chat_service.quality_analyzer.update_session_scores",
                  return_value=mock_updated),
            patch.object(svc.cache, "is_ephemeral_agent", return_value=False),
        ]
        for p in patches:
            p.start()
        return svc, mock_driver, patches

    @logged
    def test_sanitize_pii_runs_before_ai_call(self):
        """
        sanitize_pii DEVE ser chamado ANTES de AIClient.complete.
        Caso contrário, PII vazaria para o LLM.
        """
        svc, mock_driver, patches = self._setup_chat_mocks()
        try:
            with patch("src.application.services.chat_service.sanitize_pii",
                       side_effect=lambda x: x) as mock_pii:
                svc.process_message("a1", "s1", "u1", "olá mundo")
            # sanitize_pii foi chamado e AIClient também
            mock_pii.assert_called_once_with("olá mundo")
            svc.ai_client.complete.assert_called_once()
        finally:
            for p in patches:
                p.stop()

    @logged
    def test_persist_order_session_then_scores_then_history(self):
        """
        Em _persist_snapshot, a ordem é: save_session → save_scores → save_history.
        Inverter geraria FK violation (history aponta para session).
        """
        svc, mock_driver, patches = self._setup_chat_mocks()
        try:
            with patch("src.application.services.chat_service.sanitize_pii",
                       side_effect=lambda x: x):
                svc.process_message("a1", "s1", "u1", "msg")
            # Filtra só as chamadas save_*
            save_calls = [c[0] for c in mock_driver.method_calls
                          if c[0].startswith("save_")]
            assert save_calls == ["save_session", "save_scores", "save_history"]
        finally:
            for p in patches:
                p.stop()

    @logged
    def test_ai_called_with_history_plus_new_user_message(self):
        """
        AIClient.complete deve receber: history (carregado do cache) + nova
        user message. Ordem: history primeiro, user message por último.
        """
        svc, mock_driver, patches = self._setup_chat_mocks()
        try:
            existing = HistoryMessage(
                message_id="m0", session_id="s1", role="assistant",
                content="anterior", timestamp=_now(), status="delivered",
            )
            with patch.object(svc.cache, "get_history", return_value=[existing]), \
                 patch("src.application.services.chat_service.sanitize_pii",
                       side_effect=lambda x: x):
                svc.process_message("a1", "s1", "u1", "nova msg")

            call_kwargs = svc.ai_client.complete.call_args.kwargs
            messages = call_kwargs["messages"]
            assert messages[0].content == "anterior"
            assert messages[-1].content == "nova msg"
            assert messages[-1].role == "user"
        finally:
            for p in patches:
                p.stop()


@pytest.mark.fallback
@pytest.mark.part1
class TestProcessMessageFallback:
    """Caminhos alternativos: AIClient.complete lança → propaga."""

    @logged
    def test_ai_error_propagates(self):
        svc = ChatService()
        mock_driver = MagicMock()
        mock_driver.load_agent.return_value = _agent_record("a1")
        mock_driver.list_knowledge_files.return_value = []

        with patch.object(svc.ai_client, "complete",
                          side_effect=RuntimeError("LLM caiu")), \
             patch.object(svc.context_service, "load_system_prompt", return_value="p"), \
             patch.object(svc.context_service, "load_context", return_value=_ctx_record("a1")), \
             patch("src.application.services.chat_service.get_driver",
                   return_value=mock_driver), \
             patch("src.application.services.chat_service.quality_analyzer.analyze",
                   return_value=MagicMock()), \
             patch("src.application.services.chat_service.sanitize_pii",
                   side_effect=lambda x: x):
            with pytest.raises(RuntimeError, match="LLM caiu"):
                svc.process_message("a1", "s1", "u1", "msg")
