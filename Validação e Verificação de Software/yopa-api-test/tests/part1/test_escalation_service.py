"""
Parte 1 — Módulo: src/application/services/escalation_service.py

ESCOPO
------
Dispatch de escalação via webhook. O payload é serializado de forma
determinística (json.dumps com separators compactos) e assinado com
HMAC-SHA256 quando settings.INTERNAL_TOKEN está configurado.

PIPELINE
--------
dispatch_escalation
  └─> _dispatch_webhook
        ├─> _sign_payload(body)       (calcula assinatura)
        └─> requests.post(url, data=body, headers={..., X-Yopa-Signature: ...})

REGRA CRÍTICA (R1-12)
---------------------
O HMAC é calculado SOBRE OS BYTES que serão enviados em `data=`. Se a
serialização do payload mudar entre _sign_payload e requests.post,
a assinatura fica inválida no destino.

TIPOS DE TESTE
--------------
- unit         : _sign_payload (determinismo, formato sha256=...)
- pipeline     : ordem dispatch → _sign_payload → requests.post
- fallback     : INTERNAL_TOKEN vazio → header X-Yopa-Signature ausente
- regression   : R1-12 — payload assinado e enviado
"""
import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from tests.shared.log_helper import logged

from src.application.services import escalation_service
from src.application.services.escalation_service import (
    dispatch_escalation,
    _sign_payload,
    _dispatch_webhook,
)
from src.domain.agent import AgentContextBase, EscalationDestinationConfig
from src.domain.conversation import HistoryMessage, SessionMeta


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _meta(session_id="s1") -> SessionMeta:
    return SessionMeta(
        session_id=session_id, agent_id="a1", user_id="u1",
        model="gpt-4o", started_at=_now(),
    )


def _history():
    return [
        HistoryMessage(message_id="m1", session_id="s1", role="user",
                       content="msg do usuário", timestamp=_now(), status="delivered"),
        HistoryMessage(message_id="m2", session_id="s1", role="assistant",
                       content="resposta da IA", timestamp=_now(), status="delivered"),
    ]


@pytest.mark.unit
@pytest.mark.part1
class TestSignPayload:
    """Função _sign_payload — calcula HMAC-SHA256 sobre bytes."""

    @logged
    def test_hmac_is_deterministic(self):
        """Mesmo body + mesmo INTERNAL_TOKEN → mesma assinatura."""
        from src.infrastructure.config import settings
        with patch.object(settings, "INTERNAL_TOKEN", "chave-secreta"):
            sig1 = _sign_payload(b'{"a":1}')
            sig2 = _sign_payload(b'{"a":1}')
        assert sig1 == sig2

    @logged
    def test_different_bodies_produce_different_signatures(self):
        from src.infrastructure.config import settings
        with patch.object(settings, "INTERNAL_TOKEN", "chave"):
            assert _sign_payload(b'{"a":1}') != _sign_payload(b'{"a":2}')

    @logged
    def test_signature_has_sha256_prefix(self):
        from src.infrastructure.config import settings
        with patch.object(settings, "INTERNAL_TOKEN", "chave"):
            sig = _sign_payload(b'{}')
        assert sig.startswith("sha256=")

    @logged
    def test_signature_is_hex_after_prefix(self):
        from src.infrastructure.config import settings
        with patch.object(settings, "INTERNAL_TOKEN", "chave"):
            sig = _sign_payload(b'{}')
        hex_part = sig[len("sha256="):]
        assert len(hex_part) == 64  # SHA-256 hex
        assert all(c in "0123456789abcdef" for c in hex_part)


@pytest.mark.fallback
@pytest.mark.part1
class TestSignPayloadNoToken:
    """_sign_payload retorna None quando INTERNAL_TOKEN está vazio."""

    @logged
    def test_returns_none_when_token_empty(self):
        from src.infrastructure.config import settings
        with patch.object(settings, "INTERNAL_TOKEN", ""):
            assert _sign_payload(b'{"a":1}') is None


@pytest.mark.pipeline
@pytest.mark.regression
@pytest.mark.part1
class TestDispatchWebhookPipeline:
    """
    Regressão R1-12: validação da ordem e da preservação do payload.
    """

    @logged
    def test_post_is_called_with_signed_payload(self):
        from src.infrastructure.config import settings
        with patch.object(settings, "INTERNAL_TOKEN", "chave-secreta"), \
             patch("src.application.services.escalation_service.requests.post") as mock_post:
            _dispatch_webhook("https://example.com/hook", token=None,
                              payload={"event": "escalation", "x": 1})

        mock_post.assert_called_once()
        kwargs = mock_post.call_args.kwargs
        headers = kwargs["headers"]
        assert "X-Yopa-Signature" in headers
        assert headers["X-Yopa-Signature"].startswith("sha256=")

    @logged
    def test_payload_bytes_match_signed_bytes(self):
        """
        O body usado para calcular o HMAC deve ser EXATAMENTE o body
        enviado em requests.post(data=...). Caso contrário, a assinatura
        no destino é inválida.
        """
        from src.infrastructure.config import settings
        captured = {}

        def fake_sign(body: bytes):
            captured["signed"] = body
            return "sha256=xx"

        with patch.object(settings, "INTERNAL_TOKEN", "chave"), \
             patch.object(escalation_service, "_sign_payload", side_effect=fake_sign), \
             patch("src.application.services.escalation_service.requests.post") as mock_post:
            _dispatch_webhook("https://example.com/hook", token=None,
                              payload={"event": "escalation", "x": 1})

        sent_body = mock_post.call_args.kwargs["data"]
        assert sent_body == captured["signed"]

    @logged
    def test_authorization_bearer_header_present_when_token_passed(self):
        from src.infrastructure.config import settings
        with patch.object(settings, "INTERNAL_TOKEN", ""), \
             patch("src.application.services.escalation_service.requests.post") as mock_post:
            _dispatch_webhook("https://example.com/hook", token="tok-abc",
                              payload={"a": 1})

        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer tok-abc"


@pytest.mark.fallback
@pytest.mark.part1
class TestDispatchWebhookNoToken:
    """Sem INTERNAL_TOKEN, o POST sai sem header X-Yopa-Signature."""

    @logged
    def test_signature_header_absent_when_token_empty(self):
        from src.infrastructure.config import settings
        with patch.object(settings, "INTERNAL_TOKEN", ""), \
             patch("src.application.services.escalation_service.requests.post") as mock_post:
            _dispatch_webhook("https://example.com/hook", token=None,
                              payload={"a": 1})

        headers = mock_post.call_args.kwargs["headers"]
        assert "X-Yopa-Signature" not in headers


@pytest.mark.integration
@pytest.mark.regression
@pytest.mark.part1
class TestDispatchEscalation:
    """
    dispatch_escalation lê AgentContextBase.escalation_destination e roteia
    para a função correta. type='none' (default) → não dispara nada.
    """

    @logged
    def test_destination_none_does_not_call_requests(self):
        ctx = AgentContextBase(persona="P")
        with patch("src.application.services.escalation_service.requests.post") as mock_post:
            dispatch_escalation(
                agent_id="a1", session_id="s1", reason="automatic",
                context=ctx, meta=_meta(), history=_history(),
            )
        mock_post.assert_not_called()

    @logged
    def test_webhook_destination_dispatches_post(self):
        ctx = AgentContextBase(
            persona="P",
            escalation_destination=EscalationDestinationConfig(
                type="webhook", url="https://example.com/hook",
            ),
        )
        with patch("src.application.services.escalation_service.requests.post") as mock_post:
            dispatch_escalation(
                agent_id="a1", session_id="s1", reason="manual",
                context=ctx, meta=_meta(), history=_history(),
            )
        mock_post.assert_called_once()

    @logged
    def test_payload_contains_required_fields(self):
        """Payload deve ter event/session_id/agent_id/user_id/reason/triggered_at/last_messages."""
        ctx = AgentContextBase(
            persona="P",
            escalation_destination=EscalationDestinationConfig(
                type="webhook", url="https://example.com/hook",
            ),
        )
        with patch("src.application.services.escalation_service.requests.post") as mock_post:
            dispatch_escalation(
                agent_id="a1", session_id="s1", reason="automatic",
                context=ctx, meta=_meta(), history=_history(),
            )
        body = mock_post.call_args.kwargs["data"]
        decoded = json.loads(body.decode())
        assert decoded["event"] == "escalation"
        assert decoded["session_id"] == "s1"
        assert decoded["agent_id"] == "a1"
        assert decoded["reason"] == "automatic"
        assert "triggered_at" in decoded
        assert "last_messages" in decoded
        assert len(decoded["last_messages"]) == 2
