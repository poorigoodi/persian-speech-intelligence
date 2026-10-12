"""Analysis and extraction schemas."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TopicItem(BaseModel):
    name: str
    description: str = ""
    relevance: float | None = Field(
        default=None,
        description="Optional uncalibrated relevance score; not a calibrated probability.",
    )


class DetailedSummary(BaseModel):
    main_discussion: str = ""
    important_points: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    final_conclusions: list[str] = Field(default_factory=list)


class SentimentResult(BaseModel):
    label: Literal["Positive", "Negative", "Neutral", "Mixed", "Uncertain"]
    explanation: str
    supporting_segment_ids: list[str] = Field(default_factory=list)
    score: float | None = Field(
        default=None,
        description="Optional uncalibrated model score; not a calibrated probability.",
    )
    disclaimer: str = (
        "Text-based sentiment of transcript language only. "
        "Does not infer speaker emotional or psychological state. "
        "May be inaccurate for sarcasm, informal Persian, and context-dependent statements."
    )


class TaskItem(BaseModel):
    description: str
    assigned_to: str | None = None
    deadline: str | None = None
    source_segment_ids: list[str] = Field(default_factory=list)


class DecisionItem(BaseModel):
    description: str
    source_segment_ids: list[str] = Field(default_factory=list)


class ExtractedEntities(BaseModel):
    people: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    times: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    tasks: list[TaskItem] = Field(default_factory=list)
    decisions: list[DecisionItem] = Field(default_factory=list)
    deadlines: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    recording_id: UUID
    short_summary: str | None = None
    detailed_summary: DetailedSummary | dict[str, Any] | None = None
    topics: list[TopicItem] | list[dict[str, Any]] | None = None
    sentiment: SentimentResult | dict[str, Any] | None = None
    extracted_entities: ExtractedEntities | dict[str, Any] | None = None
    action_items: list[TaskItem] | list[dict[str, Any]] | None = None
    decisions: list[DecisionItem] | list[dict[str, Any]] | None = None


class ExportResponse(BaseModel):
    recording_id: UUID
    format: Literal["json", "txt", "markdown"]
    content: str
    filename: str
