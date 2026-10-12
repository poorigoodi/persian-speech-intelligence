"""Recording upload, listing, status, delete, and dashboard endpoints."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.deps import AppSettings, DbSession, require_api_key
from app.core.exceptions import ConflictError, NotFoundError
from app.db.repositories import (
    AnalysisRepository,
    JobRepository,
    RecordingRepository,
    TranscriptRepository,
)
from app.models.recording import ProcessingJob, ProcessingStatus, Recording
from app.schemas.common import MessageResponse
from app.schemas.recording import (
    DashboardStats,
    JobStatusResponse,
    RecordingCreateResponse,
    RecordingDetail,
    RecordingListResponse,
    RecordingSummary,
)
from app.services.audio_service import AudioService
from app.services.embedding_service import EmbeddingService

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(db: DbSession) -> DashboardStats:
    stats = RecordingRepository(db).stats()
    return DashboardStats(**stats)


@router.post(
    "",
    response_model=RecordingCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_recording(
    db: DbSession,
    settings: AppSettings,
    file: UploadFile = File(...),
) -> RecordingCreateResponse:
    audio_service = AudioService(settings)
    meta = await audio_service.save_upload(file)

    recording = Recording(
        original_filename=meta["original_filename"],
        storage_path=meta["storage_path"],
        content_type=meta.get("content_type"),
        file_size_bytes=meta["file_size_bytes"],
        duration_seconds=meta["duration_seconds"],
        sample_rate=meta.get("sample_rate"),
        processing_status=ProcessingStatus.PENDING,
    )
    recording_repo = RecordingRepository(db)
    job_repo = JobRepository(db)
    recording_repo.create(recording)
    job = ProcessingJob(
        recording_id=recording.id,
        status=ProcessingStatus.PENDING,
        progress=0,
        current_step="queued",
    )
    job_repo.create(job)
    db.commit()

    return RecordingCreateResponse(
        recording_id=recording.id,
        job_id=job.id,
        status=ProcessingStatus.PENDING,
        original_filename=recording.original_filename,
    )


@router.get("", response_model=RecordingListResponse)
def list_recordings(
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: ProcessingStatus | None = Query(default=None, alias="status"),
) -> RecordingListResponse:
    items, total = RecordingRepository(db).list(
        limit=limit, offset=offset, status=status_filter
    )
    return RecordingListResponse(
        items=[RecordingSummary.model_validate(item) for item in items],
        total=total,
    )


@router.get("/{recording_id}", response_model=RecordingDetail)
def get_recording(recording_id: UUID, db: DbSession) -> RecordingDetail:
    recording = RecordingRepository(db).get(recording_id)
    if recording is None:
        raise NotFoundError("Recording not found.")
    return RecordingDetail.model_validate(recording)


@router.get("/{recording_id}/status", response_model=JobStatusResponse)
def get_status(recording_id: UUID, db: DbSession) -> JobStatusResponse:
    recording = RecordingRepository(db).get(recording_id)
    if recording is None:
        raise NotFoundError("Recording not found.")
    job = JobRepository(db).get_latest_for_recording(recording_id)
    return JobStatusResponse(
        recording_id=recording_id,
        job_id=job.id if job else None,
        status=recording.processing_status,
        progress=job.progress if job else (
            100 if recording.processing_status == ProcessingStatus.COMPLETED else 0
        ),
        current_step=job.current_step if job else None,
        error_message=recording.error_message or (job.error_message if job else None),
        started_at=job.started_at if job else None,
        completed_at=job.completed_at if job else None,
    )


@router.delete("/{recording_id}", response_model=MessageResponse)
def delete_recording(
    recording_id: UUID,
    db: DbSession,
    settings: AppSettings,
) -> MessageResponse:
    recording_repo = RecordingRepository(db)
    recording = recording_repo.get(recording_id)
    if recording is None:
        raise NotFoundError("Recording not found.")

    if recording.processing_status == ProcessingStatus.PROCESSING:
        raise ConflictError("Cannot delete a recording while it is processing.")

    storage_path = recording.storage_path
    TranscriptRepository(db).delete_for_recording(recording_id)
    AnalysisRepository(db).delete_for_recording(recording_id)
    recording_repo.delete(recording)
    db.commit()

    AudioService(settings).delete_storage_file(storage_path)
    AudioService(settings).cleanup_temp(recording_id)
    EmbeddingService(settings).delete_recording_index(recording_id)

    # Avoid exposing absolute paths
    _ = Path(storage_path).name
    return MessageResponse(message="Recording and associated data deleted.")
