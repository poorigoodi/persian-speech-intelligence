"""Health endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()
