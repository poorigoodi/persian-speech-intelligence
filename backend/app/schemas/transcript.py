"""Transcript response schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    segment_index: int
    start_time: float
    end_time: float
    original_text: str
    normalized_text: str
    avg_logprob: float | None = None


class TranscriptResponse(BaseModel):
    recording_id: UUID
    language: str | None = None
    duration_seconds: float | None = None
    full_text: str
    full_text_normalized: str
    segments: list[TranscriptSegmentOut] = Field(default_factory=list)
