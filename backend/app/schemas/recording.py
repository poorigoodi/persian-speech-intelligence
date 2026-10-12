"""Recording and job status schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.recording import ProcessingStatus


class RecordingCreateResponse(BaseModel):
    """Response returned after a successful upload."""

    recording_id: UUID
    job_id: UUID
    status: ProcessingStatus
    original_filename: str
    message: str = "Recording uploaded and queued for processing."


class RecordingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    duration_seconds: float | None = None
    language: str | None = None
    processing_status: ProcessingStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class RecordingDetail(RecordingSummary):
    file_size_bytes: int | None = None
    sample_rate: int | None = None
    content_type: str | None = None


class JobStatusResponse(BaseModel):
    recording_id: UUID
    job_id: UUID | None = None
    status: ProcessingStatus
    progress: int = Field(ge=0, le=100)
    current_step: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class RecordingListResponse(BaseModel):
    items: list[RecordingSummary]
    total: int


class DashboardStats(BaseModel):
    total_recordings: int
    completed: int
    processing: int
    pending: int
    failed: int
