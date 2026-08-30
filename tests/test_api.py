import pytest
from fastapi.testclient import TestClient

from aetherforge.api.main import app, bootstrap


@pytest.fixture(scope="module")
def client():
    bootstrap()
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["knowledge_ready"] is True


def test_ask_creates_hitl_and_citations(client):
    res = client.post("/api/ask", json={"query": "How do we roll back a failed Kubernetes production release?"})
    assert res.status_code == 200
    body = res.json()
    assert body["citations"]
    assert body["proposed_ticket"]["jenkins_job"]
    assert body["requires_hitl"] is True
    assert body["review_id"]


def test_hitl_approve_writes_jira(client):
    asked = client.post(
        "/api/ask",
        json={"query": "PostgreSQL replica lag is over 30 seconds. Escalate and open a change."},
    ).json()
    review_id = asked["review_id"]
    approved = client.post(f"/api/hitl/{review_id}/approve", json={"reviewer": "test", "feedback": "ok"}).json()
    assert approved["status"] == "approved"
    assert approved["issue"]["key"].startswith("AF-")
    board = client.get("/api/jira/issues").json()
    keys = [t["key"] for col in board["columns"].values() for t in col]
    assert approved["issue"]["key"] in keys


def test_knowledge_and_overview(client):
    docs = client.get("/api/knowledge").json()
    assert len(docs) >= 8
    overview = client.get("/api/overview").json()
    assert overview["documents"] == len(docs)


def test_metrics_and_dashboard(client):
    assert client.get("/metrics").status_code == 200
    page = client.get("/")
    assert page.status_code == 200
    assert b"AetherForge" in page.content
