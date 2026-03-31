from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.main import create_app

app: FastAPI = create_app()


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "app": "OmniRAG"}
