"""
Integration tests for data and analytics endpoints:
  GET    /data/chat                                  — conversation listing
  GET    /data/chat/{session_id}                     — full session history
  DELETE /data/chat/{session_id}                     — session removal
  GET    /data/chat/{session_id}/insights/sentiment  — local NLP sentiment
  GET    /data/chat/{session_id}/insights/topics     — local NLP topics
  GET    /data/chat/{session_id}/insights/metrics    — session metrics
  GET    /data/analytics/summary                     — aggregated summary
Covers: insights Redis->driver fallback (R1-8), analytics segments (R1-9).
"""
import uuid
import pytest
from unittest.mock import patch
from src.infrastructure.ai.client import AIClient, AIResponse, AIUsage

from tests.shared.log_helper import logged


def _send_and_end(client, headers, agent_id, session_id=None):
    """Sends a message and ends the session (persists to driver)."""
    sid = session_id or str(uuid.uuid4())
    client.post("/chat", headers=headers, json={
        "session_id": sid,
        "user_id": "user_data_test",
        "message": "I need support with my order.",
    })
    client.post(f"/chat/{sid}/end", headers=headers)
    return sid


@pytest.mark.part2
class TestDataChat:
    @logged
    def test_list_chats_empty_initially(self, client, agent):
        _, _, headers = agent
        resp = client.get("/data/chat", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @logged
    def test_list_chats_after_session_end(self, client, agent, mock_ai):
        _, _, headers = agent
        _send_and_end(client, headers, None)
        resp = client.get("/data/chat", headers=headers)
        assert resp.json()["total"] == 1

    @logged
    def test_get_chat_detail(self, client, agent, mock_ai):
        agent_id, _, headers = agent
        sid = _send_and_end(client, headers, agent_id)
        resp = client.get(f"/data/chat/{sid}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["session"]["session_id"] == sid
        assert len(body["conversation"]) == 2

    @logged
    def test_get_chat_not_found(self, client, agent):
        _, _, headers = agent
        resp = client.get("/data/chat/nonexistent-id", headers=headers)
        assert resp.status_code == 404

    @logged
    def test_delete_chat(self, client, agent, mock_ai):
        agent_id, _, headers = agent
        sid = _send_and_end(client, headers, agent_id)
        resp = client.delete(f"/data/chat/{sid}", headers=headers)
        assert resp.status_code == 204
        assert (client.get(f"/data/chat/{sid}", headers=headers)
                .status_code == 404)


@pytest.mark.part2
class TestInsights:
    @logged
    def test_sentiment_insight(self, client, agent, mock_ai):
        agent_id, _, headers = agent
        sid = _send_and_end(client, headers, agent_id)
        resp = client.get(
            f"/data/chat/{sid}/insights/sentiment", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == sid
        assert "sentiment" in body
        assert body["sentiment"]["label"] in (
            "positive", "neutral", "negative"
        )

    @logged
    def test_topics_insight(self, client, agent, mock_ai):
        agent_id, _, headers = agent
        sid = _send_and_end(client, headers, agent_id)
        resp = client.get(
            f"/data/chat/{sid}/insights/topics", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "topics" in body
        assert "detected" in body["topics"]

    @logged
    def test_metrics_insight(self, client, agent, mock_ai):
        agent_id, _, headers = agent
        sid = _send_and_end(client, headers, agent_id)
        resp = client.get(
            f"/data/chat/{sid}/insights/metrics", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["metrics"]["total_messages"] == 2
        assert body["metrics"]["resolution"] == "open"

    @logged
    def test_insights_fallback_to_driver_when_redis_empty(
        self, client, agent, mock_ai
    ):
        """R1-8: insights endpoint falls back to driver when Redis empty."""
        agent_id, _, headers = agent
        sid = _send_and_end(client, headers, agent_id)

        # Evict scores from Redis to force driver fallback
        from src.infrastructure.cache.redis_client import CacheClient
        cache = CacheClient()
        cache._redis.delete(f"session:{sid}:scores")

        resp = client.get(
            f"/data/chat/{sid}/insights/sentiment", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["session_id"] == sid


@pytest.mark.part2
class TestAnalytics:
    @logged
    def test_summary_empty_with_no_sessions(self, client, agent):
        _, _, headers = agent
        resp = client.get("/data/analytics/summary", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["summary"]["total_chats"] == 0

    @logged
    def test_summary_after_session(self, client, agent, mock_ai):
        agent_id, _, headers = agent
        _send_and_end(client, headers, agent_id)
        resp = client.get("/data/analytics/summary", headers=headers)
        assert resp.json()["summary"]["total_chats"] == 1

    @logged
    def test_analytics_full_endpoint(self, client, agent, mock_ai):
        agent_id, _, headers = agent
        _send_and_end(client, headers, agent_id)
        resp = client.get("/data/analytics", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "summary"   in body
        assert "patterns"  in body
        assert "sentiment" in body
        assert "users"     in body
        assert "timeline"  in body

    @logged
    def test_segments_populated_from_user_context(self, client, mock_ai):
        """R1-9: analytics segments must come from UserContext."""
        resp = client.post("/agent", json={
            "name": "Segment Agent",
            "owner": "owner",
            "context": {"segment": "premium"},
        })
        assert resp.status_code == 201
        data = resp.json()
        agent_id = data["agent_id"]
        headers = {"Authorization": f"Bearer {data['api_key']}"}

        sid = str(uuid.uuid4())
        client.post("/chat", headers=headers, json={
            "session_id": sid,
            "user_id": "premium_user_1",
            "message": "hello",
        })
        client.post(f"/chat/{sid}/end", headers=headers)

        resp = client.get("/data/analytics/users", headers=headers)
        assert resp.status_code == 200
        segments = resp.json().get("users", {}).get("segments", [])
        segment_names = [s["segment"] for s in segments]
        assert "premium" in segment_names
