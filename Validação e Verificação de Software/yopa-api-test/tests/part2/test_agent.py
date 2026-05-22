"""
Integration tests for agent endpoints:
  POST   /agent                  — creation, API Key generation
  GET    /agent                  — authenticated agent data
  GET    /agent/context          — current context with version
  GET    /agent/context/history  — version history
  GET    /agent/metrics          — aggregated session metrics
  PUT    /agent/context          — context update with version increment
  PATCH  /agent                  — name update
  DELETE /agent                  — removes agent and associated data
"""
import io
import uuid
from unittest.mock import patch, MagicMock

import httpx
import pytest

from tests.shared.log_helper import logged


AGENT_PAYLOAD = {
    "name": "Support Bot",
    "owner": "acme_corp",
    "context": {
        "tone": "formal",
        "language": "pt",
        "persona": "Assistente de suporte",
    },
}


@pytest.mark.part2
class TestCreateAgent:
    @logged
    def test_returns_201_with_agent_id_and_api_key(self, client):
        resp = client.post("/agent", json=AGENT_PAYLOAD)
        assert resp.status_code == 201
        body = resp.json()
        assert "agent_id" in body
        assert "api_key" in body
        assert "created_at" in body

    @logged
    def test_api_key_contains_agent_id(self, client):
        resp = client.post("/agent", json=AGENT_PAYLOAD)
        body = resp.json()
        assert body["api_key"].startswith(body["agent_id"] + ".")

    @logged
    def test_missing_name_returns_422(self, client):
        resp = client.post("/agent", json={"owner": "x", "context": {}})
        assert resp.status_code == 422

    @logged
    def test_missing_owner_returns_422(self, client):
        resp = client.post("/agent", json={"name": "x", "context": {}})
        assert resp.status_code == 422


@pytest.mark.part2
class TestGetAgent:
    @logged
    def test_returns_agent_data(self, client, agent):
        agent_id, _, headers = agent
        resp = client.get("/agent", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_id"] == agent_id
        assert body["name"] == "Test Agent"
        assert body["owner"] == "test_owner"

    @logged
    def test_invalid_key_returns_401(self, client):
        resp = client.get("/agent",
                          headers={"Authorization": "Bearer fake.key"})
        assert resp.status_code == 401

    @logged
    def test_missing_auth_returns_403(self, client):
        resp = client.get("/agent")
        assert resp.status_code in (401, 403)


@pytest.mark.part2
class TestGetContext:
    @logged
    def test_returns_context_with_version(self, client, agent):
        _, _, headers = agent
        resp = client.get("/agent/context", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["version"] == 1
        assert body["tone"] == "formal"
        assert body["language"] == "pt"

    @logged
    def test_context_history_has_one_entry_after_create(self, client, agent):
        _, _, headers = agent
        resp = client.get("/agent/context/history", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["versions"]) == 1
        assert body["versions"][0]["version"] == 1


@pytest.mark.part2
class TestUpdateContext:
    @logged
    def test_increments_version(self, client, agent):
        _, _, headers = agent
        resp = client.put("/agent/context", headers=headers,
                          json={"tone": "informal", "language": "en"})
        assert resp.status_code == 200
        assert resp.json()["version"] == 2

    @logged
    def test_history_grows_after_update(self, client, agent):
        _, _, headers = agent
        client.put("/agent/context", headers=headers,
                   json={"tone": "informal"})
        resp = client.get("/agent/context/history", headers=headers)
        assert len(resp.json()["versions"]) == 2

    @logged
    def test_changes_field_reflects_updated_keys(self, client, agent):
        _, _, headers = agent
        client.put("/agent/context", headers=headers,
                   json={"tone": "informal"})
        resp = client.get("/agent/context/history", headers=headers)
        versions = resp.json()["versions"]
        latest = next(v for v in versions if v["version"] == 2)
        assert "tone" in latest["changes"]

    @logged
    def test_context_reflects_new_values(self, client, agent):
        _, _, headers = agent
        client.put("/agent/context", headers=headers,
                   json={"tone": "informal"})
        resp = client.get("/agent/context", headers=headers)
        assert resp.json()["tone"] == "informal"


@pytest.mark.part2
class TestGetMetrics:
    @logged
    def test_returns_zero_metrics_with_no_sessions(self, client, agent):
        agent_id, _, headers = agent
        resp = client.get("/agent/metrics", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_id"] == agent_id
        assert body["total_sessions"] == 0
        assert body["total_messages"] == 0
        assert body["resolution_rate"] == 0.0
        assert body["escalation_rate"] == 0.0


@pytest.mark.part2
class TestDeleteAgent:
    @logged
    def test_returns_deleted_at(self, client, agent):
        _, _, headers = agent
        resp = client.delete("/agent", headers=headers)
        assert resp.status_code == 200
        assert "deleted_at" in resp.json()

    @logged
    def test_agent_not_accessible_after_delete(self, client, agent):
        _, _, headers = agent
        client.delete("/agent", headers=headers)
        resp = client.get("/agent", headers=headers)
        assert resp.status_code == 401


@pytest.mark.part2
class TestKnowledgeBase:
    def _upload(self, client, headers, filename, content,
                content_type="text/csv"):
        return client.post(
            "/agent/knowledge/upload",
            headers=headers,
            files={"file": (filename, content, content_type)},
        )

    @logged
    def test_upload_csv_returns_201_with_metadata(self, client, agent):
        _, _, headers = agent
        csv = b"titulo,conteudo\nHorario,Seg a Sex 9h-18h\n"
        resp = self._upload(client, headers, "base.csv", csv)
        assert resp.status_code == 201
        body = resp.json()
        assert body["filename"] == "base.csv"
        assert body["file_type"] == "csv"
        assert body["record_count"] == 1
        assert "file_id" in body
        assert "uploaded_at" in body

    @logged
    def test_list_reflects_uploaded_files(self, client, agent):
        _, _, headers = agent
        self._upload(client, headers, "a.csv",
                     b"titulo,conteudo\nA,B\n")
        self._upload(client, headers, "b.csv",
                     b"titulo,conteudo\nC,D\nE,F\n")
        resp = client.get("/agent/knowledge", headers=headers)
        files = resp.json()["files"]
        assert len(files) == 2
        names = {f["filename"] for f in files}
        assert names == {"a.csv", "b.csv"}

    @logged
    def test_list_isolated_between_agents(self, client):
        resp1 = client.post("/agent",
                            json={"name": "Agent1", "owner": "o1",
                                  "context": {}})
        resp2 = client.post("/agent",
                            json={"name": "Agent2", "owner": "o2",
                                  "context": {}})
        h1 = {"Authorization": f"Bearer {resp1.json()['api_key']}"}
        h2 = {"Authorization": f"Bearer {resp2.json()['api_key']}"}
        self._upload(client, h1, "data.csv",
                     b"titulo,conteudo\nA,B\n")
        resp = client.get("/agent/knowledge", headers=h2)
        assert resp.json()["files"] == []

    @logged
    def test_delete_removes_file(self, client, agent):
        _, _, headers = agent
        upload = self._upload(client, headers, "del.csv",
                              b"titulo,conteudo\nA,B\n")
        file_id = upload.json()["file_id"]
        resp = client.delete(f"/agent/knowledge/{file_id}",
                             headers=headers)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    @logged
    def test_delete_nonexistent_returns_404(self, client, agent):
        _, _, headers = agent
        resp = client.delete("/agent/knowledge/nonexistent-id",
                             headers=headers)
        assert resp.status_code == 404


@pytest.mark.part2
class TestSoftDeletes:
    @logged
    def test_deleted_agent_returns_401_on_auth(self, client, agent):
        _, _, headers = agent
        client.delete("/agent", headers=headers)
        resp = client.post("/chat", headers=headers, json={
            "session_id": "s1", "user_id": "u1", "message": "hi",
        })
        assert resp.status_code in (401, 403)

    @logged
    def test_deleted_session_returns_404(self, client, agent, mock_ai):
        _, _, headers = agent
        sid = str(uuid.uuid4())
        client.post("/chat", headers=headers, json={
            "session_id": sid, "user_id": "u1", "message": "hi",
        })
        client.post(f"/chat/{sid}/end", headers=headers)
        resp = client.delete(f"/data/chat/{sid}", headers=headers)
        assert resp.status_code == 204
        resp2 = client.get(f"/data/chat/{sid}", headers=headers)
        assert resp2.status_code == 404

    @logged
    def test_purge_deleted_removes_agent_after_cutoff(
        self, client, agent, patch_env
    ):
        from datetime import datetime, timezone, timedelta
        from src.infrastructure.persistence.factory import get_driver
        agent_id, _, headers = agent
        client.delete("/agent", headers=headers)
        future = (
            datetime.now(timezone.utc) + timedelta(days=1)
        ).isoformat()
        result = get_driver().purge_deleted(before=future)
        assert result["agents_purged"] >= 1
