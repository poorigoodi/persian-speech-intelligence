"""LLM provider factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.local_provider import LocalLLMProvider
from app.llm.openai_compatible import OpenAICompatibleProvider


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    if settings.llm_provider == "local":
        return LocalLLMProvider(settings)
    return OpenAICompatibleProvider(settings)
