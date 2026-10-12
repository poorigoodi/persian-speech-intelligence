"""Audio validation helper tests (no FFmpeg required)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.exceptions import AudioValidationError
from app.services.audio_service import AudioService
from app.utils.files import SAFE_AUDIO_EXTENSIONS


def test_supported_extensions() -> None:
    assert ".wav" in SAFE_AUDIO_EXTENSIONS
    assert ".mp3" in SAFE_AUDIO_EXTENSIONS
    assert ".exe" not in SAFE_AUDIO_EXTENSIONS


def test_duration_reject_too_short(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        _env_file=None,
        database_url="sqlite+pysqlite:///:memory:",
        upload_dir=tmp_path,
        temp_dir=tmp_path,
        min_audio_duration_seconds=1.0,
        max_audio_duration_seconds=60.0,
    )
    service = AudioService(settings)
    path = tmp_path / "short.wav"
    path.write_bytes(b"RIFF")

    monkeypatch.setattr(
        "app.services.audio_service.probe_audio",
        lambda _p: {"streams": [{"codec_type": "audio", "sample_rate": "16000", "channels": 1}], "format": {"duration": "0.1"}},
    )
    monkeypatch.setattr(
        "app.services.audio_service.extract_audio_info",
        lambda _probe: {"duration": 0.1, "sample_rate": 16000, "channels": 1},
    )

    with pytest.raises(AudioValidationError):
        service.validate_stored_file(path)
    assert not path.exists()
