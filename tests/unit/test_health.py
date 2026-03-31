"""Unit tests for the /v1/health liveness endpoint.

Uses FastAPI's TestClient (sync) — no DB or Qdrant required.
"""

from fastapi.testclient import TestClient

from apps.api.main import create_app

client = TestClient(create_app(), raise_server_exceptions=True)


def test_health_returns_200() -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200


def test_health_returns_ok_status() -> None:
    response = client.get("/v1/health")
    body = response.json()
    assert body["status"] == "ok"


def test_health_returns_version() -> None:
    response = client.get("/v1/health")
    body = response.json()
    assert "version" in body
    assert isinstance(body["version"], str)
