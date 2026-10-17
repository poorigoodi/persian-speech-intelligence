"""OpenAI-compatible chat completions provider."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.llm.base import LLMMessage, LLMProvider, LLMResponse

logger = get_logger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    """Works with OpenAI, Azure OpenAI-compatible gateways, and similar APIs."""

    def __init__(
        self,
        settings: Settings,
        *,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.settings = settings
        self.base_url = (base_url or settings.llm_effective_base_url()).rstrip("/")
        self.model = model or settings.llm_effective_model()
        self.api_key = api_key if api_key is not None else settings.llm_api_key
        self.timeout = httpx.Timeout(
            connect=settings.llm_connect_timeout_seconds,
            read=settings.llm_timeout_seconds,
            write=settings.llm_connect_timeout_seconds,
            pool=settings.llm_connect_timeout_seconds,
        )

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_json: bool = False,
    ) -> LLMResponse:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        token_budget = (
            self.settings.llm_max_tokens if max_tokens is None else max_tokens
        )
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": (
                self.settings.llm_temperature if temperature is None else temperature
            ),
            "max_tokens": token_budget,
        }

        # Not all providers support response_format; try then fall back.
        if response_json:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await self._post(client, headers, payload)
                if response.status_code >= 400 and response_json:
                    payload.pop("response_format", None)
                    logger.info(
                        "Provider rejected response_format; retrying without it."
                    )
                    response = await self._post(client, headers, payload)
        except httpx.ConnectError as exc:
            raise LLMError(
                f"Cannot reach LLM server at {self.base_url}. "
                "Start Ollama/llama.cpp/vLLM and check LOCAL_LLM_BASE_URL."
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMError(
                "LLM request timed out. "
                "Increase LLM_TIMEOUT_SECONDS or reduce analysis load."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc

        if response.status_code >= 400:
            # Never include API keys; truncate body
            body = (response.text or "")[:400]
            raise LLMError(
                f"LLM provider returned HTTP {response.status_code}.",
                details={"body": body},
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise LLMError("LLM provider returned invalid JSON.") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unexpected LLM response structure.") from exc

        if content is None:
            content = ""

        return LLMResponse(content=str(content), raw=data, model=self.model)

    async def _post(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> httpx.Response:
        logger.info(
            "LLM request model=%s max_tokens=%s url=%s/chat/completions",
            self.model,
            payload.get("max_tokens"),
            self.base_url,
        )
        return await client.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
