"""Structured LLM output parsing tests."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.core.exceptions import LLMError
from app.llm.json_utils import extract_json_object, parse_structured
from app.schemas.analysis import DetailedSummary, SentimentResult


class Tiny(BaseModel):
    value: int


def test_extract_json_from_fence() -> None:
    text = 'Here is JSON:\n```json\n{"value": 3}\n```'
    assert extract_json_object(text) == {"value": 3}


def test_parse_structured_ok() -> None:
    result = parse_structured('{"value": 7}', Tiny)
    assert result.value == 7


def test_parse_structured_invalid() -> None:
    with pytest.raises(LLMError):
        parse_structured('{"value": "nope"}', Tiny)


def test_sentiment_schema_defaults() -> None:
    result = SentimentResult(label="Neutral", explanation="خنثی")
    assert "Text-based sentiment" in result.disclaimer


def test_detailed_summary_empty_lists() -> None:
    summary = DetailedSummary()
    assert summary.decisions == []
    assert summary.action_items == []


def test_combined_analysis_payload_parses() -> None:
    from app.services.analysis_pipeline import CombinedAnalysisPayload

    raw = """
    {
      "short_summary": "خلاصه",
      "detailed_summary": {"main_discussion": "بحث", "important_points": []},
      "topics": [{"name": "بودجه", "description": ""}],
      "sentiment": {"label": "Neutral", "explanation": "خنثی"},
      "extracted_entities": {"people": ["علی"], "keywords": ["پروژه"]}
    }
    """
    payload = parse_structured(raw, CombinedAnalysisPayload)
    assert payload.short_summary == "خلاصه"
    assert payload.topics[0].name == "بودجه"
    assert payload.sentiment is not None
    assert payload.sentiment.label == "Neutral"
    assert payload.extracted_entities.people == ["علی"]
