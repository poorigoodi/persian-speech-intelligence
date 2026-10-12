"""Structured application logging configuration."""

from __future__ import annotations

import logging
import sys
from typing import Any

SENSITIVE_KEYS = {"api_key", "llm_api_key", "password", "secret", "token", "authorization"}


class SensitiveDataFilter(logging.Filter):
    """Redact common secret field names from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, dict):
            record.args = {
                key: ("***REDACTED***" if key.lower() in SENSITIVE_KEYS else value)
                for key, value in record.args.items()
            }
        return True


def setup_logging(level: str = "INFO") -> None:
    """Configure root logging for the application."""
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(SensitiveDataFilter())

    root.setLevel(level)
    root.addHandler(handler)

    # Reduce noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)


def safe_extra(**kwargs: Any) -> dict[str, Any]:
    """Build a logging extras dict with secrets redacted."""
    return {
        key: ("***REDACTED***" if key.lower() in SENSITIVE_KEYS else value)
        for key, value in kwargs.items()
    }
