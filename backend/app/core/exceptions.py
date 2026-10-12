"""Application-specific exception hierarchy."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error with optional HTTP status and public detail."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: str = "app_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        kwargs.setdefault("code", "not_found")
        super().__init__(message, status_code=404, **kwargs)


class ValidationAppError(AppError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("code", "validation_error")
        super().__init__(message, status_code=400, **kwargs)


class AudioValidationError(ValidationAppError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("code", "audio_validation_error")
        super().__init__(message, **kwargs)


class ProcessingError(AppError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("code", "processing_error")
        super().__init__(message, status_code=500, **kwargs)


class ConflictError(AppError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("code", "conflict")
        super().__init__(message, status_code=409, **kwargs)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized", **kwargs: Any) -> None:
        kwargs.setdefault("code", "unauthorized")
        super().__init__(message, status_code=401, **kwargs)


class ServiceUnavailableError(AppError):
    def __init__(self, message: str = "Service unavailable", **kwargs: Any) -> None:
        kwargs.setdefault("code", "service_unavailable")
        super().__init__(message, status_code=503, **kwargs)


class LLMError(AppError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("code", "llm_error")
        super().__init__(message, status_code=502, **kwargs)
