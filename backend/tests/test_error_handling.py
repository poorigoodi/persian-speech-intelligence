"""API error handling tests."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def test_chat_missing_recording(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/recordings/{uuid.uuid4()}/chat",
        json={"question": "موضوع جلسه چه بود؟"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"


def test_transcript_missing(client: TestClient) -> None:
    response = client.get(f"/api/v1/recordings/{uuid.uuid4()}/transcript")
    assert response.status_code == 404
