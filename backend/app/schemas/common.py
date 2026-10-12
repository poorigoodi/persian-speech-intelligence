"""Shared API response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str


class ReadyResponse(BaseModel):
    status: str
    database: bool
    storage: bool
    details: dict[str, Any] = {}


class MessageResponse(BaseModel):
    message: str
