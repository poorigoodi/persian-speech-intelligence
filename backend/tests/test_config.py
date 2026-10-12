"""Configuration validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_defaults() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://psi:psi@localhost:5432/persian_speech",
    )
    assert settings.whisper_model == "small"
    assert settings.whisper_language == "fa"
    assert settings.max_upload_bytes == 100 * 1024 * 1024


def test_chunk_overlap_validation() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            chunk_size_chars=100,
            chunk_overlap_chars=100,
            database_url="postgresql+psycopg://psi:psi@localhost:5432/persian_speech",
        )


def test_cors_origin_list() -> None:
    settings = Settings(
        _env_file=None,
        cors_origins="http://a,http://b",
        database_url="postgresql+psycopg://psi:psi@localhost:5432/persian_speech",
    )
    assert settings.cors_origin_list == ["http://a", "http://b"]
