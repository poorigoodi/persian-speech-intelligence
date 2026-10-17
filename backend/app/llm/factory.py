"""LLM provider factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.local_provider import LocalLLMProvider
from app.llm.openai_compatible import OpenAICompatibleProvider


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """General LLM for summary / extraction / QA (Qwen3-2B by default)."""
    settings = settings or get_settings()
    if settings.llm_provider == "local":
        return LocalLLMProvider(settings)
    return OpenAICompatibleProvider(settings)


def get_asr_polish_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """LLM for ASR transcript polish (optional dedicated LoRA model id)."""
    settings = settings or get_settings()
    model = settings.asr_polish_effective_model()
    if settings.llm_provider == "local":
        return LocalLLMProvider(settings, model=model)
    return OpenAICompatibleProvider(settings, model=model)


def get_sentiment_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Sentiment-only LLM (Qwen3-4B by default; same endpoint, different model).

    Prefer enabling only when SENTIMENT_USE_SEPARATE_MODEL=true — loading a second
    model on one GPU often causes long stalls / timeouts.
    """
    settings = settings or get_settings()
    model = settings.sentiment_effective_model()
    if settings.llm_provider == "local":
        return LocalLLMProvider(settings, model=model)
    return OpenAICompatibleProvider(settings, model=model)
