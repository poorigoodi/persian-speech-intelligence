"""Helpers for parsing and validating structured LLM outputs."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.exceptions import LLMError
from app.core.logging import get_logger

logger = get_logger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def extract_json_object(text: str) -> Any:
    """Extract a JSON object/array from raw LLM text."""
    cleaned = text.strip()
    fence = _JSON_FENCE.search(cleaned)
    if fence:
        cleaned = fence.group(1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # Try to locate first { or [
        start_candidates = [i for i in (cleaned.find("{"), cleaned.find("[")) if i >= 0]
        if not start_candidates:
            raise LLMError("LLM response did not contain JSON.") from exc
        start = min(start_candidates)
        snippet = cleaned[start:]
        # Balance braces/brackets naively
        for end in range(len(snippet), 0, -1):
            candidate = snippet[:end].rstrip().rstrip(",")
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        raise LLMError("Failed to parse JSON from LLM response.") from exc


def parse_structured[T: BaseModel](text: str, model: type[T]) -> T:
    """Parse LLM text into a Pydantic model with validation."""
    data = extract_json_object(text)
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        logger.warning("LLM structured output validation failed: %s", exc)
        raise LLMError(
            "LLM returned structured output that failed validation.",
            details={"errors": exc.errors()},
        ) from exc
