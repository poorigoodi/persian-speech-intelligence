"""Question-answering chat schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class EvidenceSegment(BaseModel):
    segment_id: UUID | None = None
    start_time: float
    end_time: float
    text: str
    score: float | None = Field(
        default=None,
        description="Optional retrieval similarity score (uncalibrated).",
    )


class ChatResponse(BaseModel):
    recording_id: UUID
    question: str
    answer: str
    grounded: bool
    evidence: list[EvidenceSegment] = Field(default_factory=list)
