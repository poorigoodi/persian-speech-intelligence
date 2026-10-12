"""Recording API tests with mocked audio validation."""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.repositories.recording_repo import RecordingRepository
from app.models.recording import ProcessingStatus, Recording


def test_list_empty(client: TestClient) -> None:
    response = client.get("/api/v1/recordings")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_stats(client: TestClient) -> None:
    response = client.get("/api/v1/recordings/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_recordings"] == 0


def test_get_missing_recording(client: TestClient) -> None:
    response = client.get(f"/api/v1/recordings/{uuid.uuid4()}")
    assert response.status_code == 404


def test_upload_mocked(client: TestClient, tmp_path, monkeypatch) -> None:
    fake_meta = {
        "original_filename": "sample.wav",
        "storage_path": str(tmp_path / "sample.wav"),
        "storage_name": "sample.wav",
        "file_size_bytes": 100,
        "duration_seconds": 2.5,
        "sample_rate": 16000,
        "content_type": "audio/wav",
    }

    with patch(
        "app.api.v1.recordings.AudioService.save_upload",
        new=AsyncMock(return_value=fake_meta),
    ):
        response = client.post(
            "/api/v1/recordings",
            files={"file": ("sample.wav", io.BytesIO(b"RIFF" + b"0" * 100), "audio/wav")},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["original_filename"] == "sample.wav"


def test_delete_recording(client: TestClient, db_session: Session, tmp_path) -> None:
    path = tmp_path / "del.wav"
    path.write_bytes(b"RIFF")
    recording = Recording(
        id=uuid.uuid4(),
        original_filename="del.wav",
        storage_path=str(path),
        processing_status=ProcessingStatus.COMPLETED,
    )
    RecordingRepository(db_session).create(recording)
    db_session.commit()

    with patch("app.api.v1.recordings.EmbeddingService.delete_recording_index"):
        response = client.delete(f"/api/v1/recordings/{recording.id}")

    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()
