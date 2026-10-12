"""Base LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    raw: dict[str, Any] = field(default_factory=dict)
    model: str | None = None


class LLMProvider(ABC):
    """Abstract LLM provider."""

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_json: bool = False,
    ) -> LLMResponse:
        """Send a chat completion request."""

    async def complete_json(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Request JSON-shaped output with provider-compatible handling."""
        response = await self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_json=True,
        )
        return response.content
