"""Optional LLM polish for garbled Persian ASR transcripts."""

from __future__ import annotations

from app.core.logging import get_logger
from app.llm.base import LLMMessage, LLMProvider
from app.utils.asr_correct import ASR_POLISH_SYSTEM, apply_asr_rules
from app.utils.persian_normalize import normalize_persian_text

logger = get_logger(__name__)


class AsrPolishService:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm

    def polish_rules_only(self, text: str) -> str:
        return normalize_persian_text(apply_asr_rules(text))

    async def polish(self, text: str, *, use_llm: bool = True) -> str:
        ruled = apply_asr_rules(text)
        if not use_llm or self.llm is None or not ruled.strip():
            return normalize_persian_text(ruled)

        messages = [
            LLMMessage(role="system", content=ASR_POLISH_SYSTEM),
            LLMMessage(
                role="user",
                content=(
                    "این transcript را اصلاح کنید:\n\n"
                    f"{ruled[:6000]}"
                ),
            ),
        ]
        try:
            response = await self.llm.chat(messages, temperature=0.0, max_tokens=1024)
            polished = (response.content or "").strip()
            # Guard: reject empty / wildly longer outputs
            if not polished or len(polished) > max(40, int(len(ruled) * 1.8)):
                logger.warning("ASR LLM polish rejected; keeping rule-based text.")
                return normalize_persian_text(ruled)
            return normalize_persian_text(apply_asr_rules(polished))
        except Exception as exc:
            logger.warning("ASR LLM polish failed (%s); keeping rule-based text.", exc)
            return normalize_persian_text(ruled)
