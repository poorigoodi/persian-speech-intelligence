"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py → repo root is parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _env_files() -> tuple[str, ...]:
    """Prefer repo-root .env, then cwd .env (local demo / Docker)."""
    candidates = [
        _REPO_ROOT / ".env",
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
    ]
    found: list[str] = []
    for path in candidates:
        resolved = str(path.resolve())
        if path.is_file() and resolved not in found:
            found.append(resolved)
    return tuple(found) or (".env",)


class Settings(BaseSettings):
    """Validated runtime settings for the Persian Speech Intelligence API."""

    model_config = SettingsConfigDict(
        env_file=_env_files(),
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

    # Whisper ASR (Faster-Whisper Medium on GPU by default)
    whisper_model: str = "medium"
    whisper_device: Literal["cpu", "cuda", "auto"] = "cuda"
    whisper_compute_type: str = "float16"
    whisper_language: str = "fa"
    whisper_auto_detect_language: bool = False
    whisper_beam_size: int = Field(default=5, ge=1, le=10)

    # Embeddings / RAG — multilingual-e5-small on CPU; FAISS on CPU; no reranker
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_device: Literal["cpu", "cuda"] = "cpu"
    chunk_size_chars: int = Field(default=500, ge=100, le=4000)
    chunk_overlap_chars: int = Field(default=80, ge=0, le=1000)
    retrieval_top_k: int = Field(default=5, ge=1, le=20)

    # LLM — Qwen3-2B-Instruct-2507 (Q4) via local OpenAI-compatible server (GPU)
    llm_provider: Literal["openai_compatible", "local"] = "local"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "Qwen3-2B-Instruct-2507"
    llm_api_key: str = ""
    # Local models are slow: long read timeout, fast connect fail.
    llm_timeout_seconds: int = Field(default=300, ge=10, le=900)
    llm_connect_timeout_seconds: float = Field(default=10.0, ge=1.0, le=60.0)
    llm_max_tokens: int = Field(default=1024, ge=256, le=16384)
    llm_analysis_max_tokens: int = Field(default=1536, ge=256, le=8192)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    # Pause between LLM calls to reduce GPU/memory thrash on small machines.
    llm_request_pause_seconds: float = Field(default=1.5, ge=0.0, le=30.0)
    analysis_transcript_max_chars: int = Field(default=8000, ge=1000, le=40000)

    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_model: str = "Qwen3-2B-Instruct-2507"

    # Sentiment — Qwen3-4B when separate mode is enabled; otherwise included in
    # the single combined analysis call (safer on one GPU / slow local servers).
    sentiment_model: str = "Qwen3-4B"
    local_sentiment_model: str = "Qwen3-4B"
    sentiment_use_separate_model: bool = False

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

    def sentiment_effective_model(self) -> str:
        if self.llm_provider == "local":
            return self.local_sentiment_model
        return self.sentiment_model


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
