"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def require_api_key(
    settings: AppSettings,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """Optional API key gate for non-localhost deployments."""
    if not settings.auth_enabled:
        return
    if not settings.api_key:
        raise UnauthorizedError("AUTH_ENABLED is true but API_KEY is not configured.")
    if x_api_key != settings.api_key:
        raise UnauthorizedError("Invalid or missing API key.")
