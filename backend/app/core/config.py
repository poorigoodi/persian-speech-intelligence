"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings for the Persian Speech Intelligence API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "Persian Speech Intelligence"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:8501,http://127.0.0.1:8501"

    # Security
    api_key: str = ""
    auth_enabled: bool = False

    # Database
    database_url: str = (
        "postgresql+psycopg://psi:psi_secret@localhost:5432/persian_speech"
    )

    # Storage
    storage_dir: Path = Path("./storage")
    upload_dir: Path = Path("./storage/uploads")
    temp_dir: Path = Path("./storage/temp")
    vector_index_dir: Path = Path("./storage/vector_indexes")

    # Upload limits
    max_upload_mb: int = Field(default=100, ge=1, le=2048)
    max_audio_duration_seconds: float = Field(default=3600.0, gt=0)
    min_audio_duration_seconds: float = Field(default=0.5, gt=0)

    # Whisper ASR
    whisper_model: str = "small"
    whisper_device: Literal["cpu", "cuda", "auto"] = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: str = "fa"
    whisper_auto_detect_language: bool = False
    whisper_beam_size: int = Field(default=5, ge=1, le=10)

    # Embeddings / RAG
    embedding_model: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    chunk_size_chars: int = Field(default=500, ge=100, le=4000)
    chunk_overlap_chars: int = Field(default=80, ge=0, le=1000)
    retrieval_top_k: int = Field(default=5, ge=1, le=20)

    # LLM
    llm_provider: Literal["openai_compatible", "local"] = "openai_compatible"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_timeout_seconds: int = Field(default=120, ge=10, le=600)
    llm_max_tokens: int = Field(default=4096, ge=256, le=16384)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_model: str = "llama3.2"

    # Worker
    worker_poll_interval_seconds: float = Field(default=2.0, ge=0.5, le=60.0)
    worker_max_concurrency: int = Field(default=1, ge=1, le=8)
    worker_max_retries: int = Field(default=2, ge=0, le=10)
    job_stale_timeout_seconds: int = Field(default=7200, ge=60)

    # Retention
    retention_days: int = Field(default=0, ge=0)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        level = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return level

    @model_validator(mode="after")
    def validate_chunk_overlap(self) -> Settings:
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError("CHUNK_OVERLAP_CHARS must be smaller than CHUNK_SIZE_CHARS")
        if self.min_audio_duration_seconds >= self.max_audio_duration_seconds:
            raise ValueError(
                "MIN_AUDIO_DURATION_SECONDS must be less than MAX_AUDIO_DURATION_SECONDS"
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        """Create required storage directories if they do not exist."""
        for path in (
            self.storage_dir,
            self.upload_dir,
            self.temp_dir,
            self.vector_index_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def llm_effective_base_url(self) -> str:
        if self.llm_provider == "local":
            return self.local_llm_base_url
        return self.llm_base_url

    def llm_effective_model(self) -> str:
        if self.llm_provider == "local":
            return self.local_llm_model
        return self.llm_model


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
