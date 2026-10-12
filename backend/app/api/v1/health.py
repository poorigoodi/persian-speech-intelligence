"""Health and readiness endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from app.api.deps import AppSettings
from app.db.session import check_database_connection
from app.schemas.common import HealthResponse, ReadyResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(settings: AppSettings) -> HealthResponse:
    """Liveness probe — does not check dependencies."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )


@router.get("/ready", response_model=ReadyResponse)
def ready(settings: AppSettings) -> ReadyResponse:
    """Readiness probe — verifies database and storage access."""
    db_ok = check_database_connection()
    storage_ok = all(
        Path(path).exists()
        for path in (settings.upload_dir, settings.temp_dir, settings.vector_index_dir)
    )
    status = "ready" if db_ok and storage_ok else "not_ready"
    return ReadyResponse(
        status=status,
        database=db_ok,
        storage=storage_ok,
        details={
            "upload_dir": str(settings.upload_dir),
            "temp_dir": str(settings.temp_dir),
            "vector_index_dir": str(settings.vector_index_dir),
        },
    )
