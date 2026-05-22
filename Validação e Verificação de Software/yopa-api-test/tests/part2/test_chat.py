"""
Integration tests for chat endpoints:
  POST /chat                        — send message, structured response
  POST /chat/{session_id}/end       — session end
  POST /chat/{session_id}/resolve   — resolve session
  POST /chat/{session_id}/escalate  — escalate session
Covers: X-Allowed-Models enforcement (R1-14), HMAC signing (R1-12),
        escalation auto/manual dispatch, multi-round tool use.
"""
import uuid
import pytest

from tests.shared.log_helper import logged


SESSION_ID = str(uuid.uuid4())

CHAT_PAYLOAD = {
    "session_id": SESSION_ID,
    "user_id": "user_123",
    "message": "Hello, I need help.",
}


@pytest.mark.part2
class TestSendMessage:
    @logged
    def test_returns_response_with_session_and_conversation(
        self, client, agent, mock_ai
    ):
        _, _, headers = agent
        resp = client.post("/chat", headers=headers, json=CHAT_PAYLOAD)
        assert resp.status_code == 200
        body = resp.json()
        assert "session" in body
        assert "conversation" in body
        assert body["session"]["session_id"] == SESSION_ID
        assert len(body["conversation"]) == 2

    @logged
    def test_conversation_has_user_and_assistant_messages(
        self, client, agent, mock_ai
    ):
        _, _, headers = agent
        resp = client.post("/chat", headers=headers, json=CHAT_PAYLOAD)
        roles = [entry["message"]["role"]
                 for entry in resp.json()["conversation"]]
        assert "user" in roles
        assert "assistant" in roles

    @logged
    def test_ai_response_content_is_returned(self, client, agent, mock_ai):
        _, _, headers = agent
        resp = client.post("/chat", headers=headers, json=CHAT_PAYLOAD)
        assistant_entries = [
            e for e in resp.json()["conversation"]
            if e["message"]["role"] == "assistant"
        ]
        assert (assistant_entries[0]["message"]["content"]
                == "Test response from AI.")

    @logged
    def test_token_usage_is_present(self, client, agent, mock_ai):
        _, _, headers = agent
        resp = client.post("/chat", headers=headers, json=CHAT_PAYLOAD)
        tokens = resp.json()["session"]["tokens"]
        assert tokens["total"] == 15

    @logged
    def test_unauthenticated_request_returns_401(self, client, mock_ai):
        resp = client.post("/chat", json=CHAT_PAYLOAD)
        assert resp.status_code in (401, 403)

    @logged
    def test_session_id_generated_when_omitted(self, client, agent, mock_ai):
        """Server generates session_id if not supplied."""
        _, _, headers = agent
        resp = client.post("/chat", headers=headers,
                           json={"user_id": "u1", "message": "hi"})
        assert resp.status_code == 200
        assert resp.json()["session"]["session_id"]


@pytest.mark.part2
class TestAllowedModels:
    """R1-14: X-Allowed-Models header enforcement by proxy."""

    @logged
    def test_allowed_model_passes(self, client, agent, mock_ai, monkeypatch):
        _, _, headers = agent
        from src.infrastructure.config import settings
        monkeypatch.setattr(settings, "AI_MODEL", "gpt-4o")
        auth_headers = {**headers, "X-Allowed-Models": "gpt-4o,gpt-3.5-turbo"}
        resp = client.post("/chat", headers=auth_headers, json=CHAT_PAYLOAD)
        assert resp.status_code == 200

    @logged
    def test_disallowed_model_returns_403(self, client, agent, mock_ai,
                                          monkeypatch):
        _, _, headers = agent
        from src.infrastructure.config import settings
        monkeypatch.setattr(settings, "AI_MODEL", "gpt-4o")
        auth_headers = {**headers, "X-Allowed-Models": "claude-3-opus"}
        resp = client.post("/chat", headers=auth_headers,
                           json={**CHAT_PAYLOAD,
                                 "session_id": str(uuid.uuid4())})
        assert resp.status_code == 403

    @logged
    def test_empty_allowed_models_header_does_not_block(
        self, client, agent, mock_ai
    ):
        """Empty header value is treated as no restriction."""
        _, _, headers = agent
        auth_headers = {**headers, "X-Allowed-Models": ""}
        resp = client.post("/chat", headers=auth_headers,
                           json={**CHAT_PAYLOAD,
                                 "session_id": str(uuid.uuid4())})
        assert resp.status_code == 200


@pytest.mark.part2
class TestSessionLifecycle:
    @logged
    def test_end_session(self, client, agent, mock_ai):
        _, _, headers = agent
        sid = str(uuid.uuid4())
        client.post("/chat", headers=headers,
                    json={**CHAT_PAYLOAD, "session_id": sid})
        resp = client.post(f"/chat/{sid}/end", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == sid
        assert "ended_at" in body

    @logged
    def test_resolve_session(self, client, agent, mock_ai):
        _, _, headers = agent
        sid = str(uuid.uuid4())
        client.post("/chat", headers=headers,
                    json={**CHAT_PAYLOAD, "session_id": sid})
        resp = client.post(f"/chat/{sid}/resolve", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["resolved"] is True

    @logged
    def test_escalate_session(self, client, agent, mock_ai):
        _, _, headers = agent
        sid = str(uuid.uuid4())
        client.post("/chat", headers=headers,
                    json={**CHAT_PAYLOAD, "session_id": sid})
        resp = client.post(f"/chat/{sid}/escalate", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["escalated"] is True

    @logged
    def test_end_nonexistent_session_returns_404(self, client, agent):
        _, _, headers = agent
        resp = client.post("/chat/nonexistent-session-id/end",
                           headers=headers)
        assert resp.status_code == 404


@pytest.mark.part2
class TestHmacSigning:
    """R1-12: HMAC-SHA256 signature on escalation webhook payloads."""

    @logged
    def test_webhook_includes_signature_when_token_set(
        self, client, mock_ai, monkeypatch
    ):
        from unittest.mock import patch as mock_patch
        from src.infrastructure.config import settings
        monkeypatch.setattr(settings, "INTERNAL_TOKEN", "test-secret-token")

        resp = client.post("/agent", json={
            "name": "HMAC Agent", "owner": "owner",
            "context": {"escalation_destination": {
                "type": "webhook",
                "url": "https://hooks.example.com/hmac",
            }},
        })
        assert resp.status_code == 201
        headers = {"Authorization": f"Bearer {resp.json()['api_key']}"}
        sid = str(uuid.uuid4())
        client.post("/chat", headers=headers,
                    json={"session_id": sid, "user_id": "u1",
                          "message": "hi"})

        with mock_patch(
            "src.application.services.escalation_service.requests.post"
        ) as mock_post:
            mock_post.return_value.status_code = 200
            client.post(f"/chat/{sid}/escalate", headers=headers)

        call_headers = mock_post.call_args.kwargs["headers"]
        assert "X-Yopa-Signature" in call_headers
        assert call_headers["X-Yopa-Signature"].startswith("sha256=")

    @logged
    def test_signature_is_valid_hmac(self, client, mock_ai, monkeypatch):
        import hmac, hashlib, json
        from unittest.mock import patch as mock_patch
        from src.infrastructure.config import settings

        secret = "verify-me-token"
        monkeypatch.setattr(settings, "INTERNAL_TOKEN", secret)

        resp = client.post("/agent", json={
            "name": "HMAC Verify", "owner": "owner",
            "context": {"escalation_destination": {
                "type": "webhook",
                "url": "https://hooks.example.com/verify",
            }},
        })
        headers = {"Authorization": f"Bearer {resp.json()['api_key']}"}
        sid = str(uuid.uuid4())
        client.post("/chat", headers=headers,
                    json={"session_id": sid, "user_id": "u1",
                          "message": "hi"})

        with mock_patch(
            "src.application.services.escalation_service.requests.post"
        ) as mock_post:
            mock_post.return_value.status_code = 200
            client.post(f"/chat/{sid}/escalate", headers=headers)

        raw_body = mock_post.call_args.kwargs["data"]
        received_sig = mock_post.call_args.kwargs["headers"]
        received_sig = received_sig["X-Yopa-Signature"]
        expected = "sha256=" + hmac.new(
            secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        assert received_sig == expected

    @logged
    def test_no_signature_when_token_empty(self, client, mock_ai, monkeypatch):
        from unittest.mock import patch as mock_patch
        from src.infrastructure.config import settings
        monkeypatch.setattr(settings, "INTERNAL_TOKEN", "")

        resp = client.post("/agent", json={
            "name": "No HMAC", "owner": "owner",
            "context": {"escalation_destination": {
                "type": "webhook",
                "url": "https://hooks.example.com/no-hmac",
            }},
        })
        headers = {"Authorization": f"Bearer {resp.json()['api_key']}"}
        sid = str(uuid.uuid4())
        client.post("/chat", headers=headers,
                    json={"session_id": sid, "user_id": "u1",
                          "message": "hi"})

        with mock_patch(
            "src.application.services.escalation_service.requests.post"
        ) as mock_post:
            mock_post.return_value.status_code = 200
            client.post(f"/chat/{sid}/escalate", headers=headers)

        call_headers = mock_post.call_args.kwargs["headers"]
        assert "X-Yopa-Signature" not in call_headers
