"""Local LLM adapter using an OpenAI-compatible local server (e.g. Ollama)."""

from __future__ import annotations

from app.core.config import Settings
from app.llm.openai_compatible import OpenAICompatibleProvider


class LocalLLMProvider(OpenAICompatibleProvider):
    """Adapter for local inference servers exposing OpenAI-compatible APIs."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(
            settings,
            base_url=settings.local_llm_base_url,
            model=settings.local_llm_model,
            api_key=settings.llm_api_key or "local",
        )
