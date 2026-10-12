"""Processing job status transition tests."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.db.repositories.job_repo import JobRepository
from app.db.repositories.recording_repo import RecordingRepository
from app.models.recording import ProcessingJob, ProcessingStatus, Recording


def test_claim_and_complete(db_session: Session) -> None:
    recording = Recording(
        id=uuid.uuid4(),
        original_filename="a.wav",
        storage_path="/tmp/a.wav",
        processing_status=ProcessingStatus.PENDING,
    )
    RecordingRepository(db_session).create(recording)
    job = ProcessingJob(
        recording_id=recording.id,
        status=ProcessingStatus.PENDING,
        progress=0,
    )
    repo = JobRepository(db_session)
    repo.create(job)
    db_session.commit()

    claimed = repo.claim_next_pending(max_retries=2)
    assert claimed is not None
    assert claimed.status == ProcessingStatus.PROCESSING
    assert claimed.attempt_count == 1

    repo.update_progress(claimed, progress=50, current_step="transcribe")
    repo.mark_completed(claimed)
    db_session.commit()

    assert claimed.status == ProcessingStatus.COMPLETED
    assert claimed.progress == 100


def test_mark_failed(db_session: Session) -> None:
    recording = Recording(
        id=uuid.uuid4(),
        original_filename="b.wav",
        storage_path="/tmp/b.wav",
        processing_status=ProcessingStatus.PENDING,
    )
    RecordingRepository(db_session).create(recording)
    job = ProcessingJob(recording_id=recording.id, status=ProcessingStatus.PENDING)
    repo = JobRepository(db_session)
    repo.create(job)
    claimed = repo.claim_next_pending(max_retries=0)
    assert claimed is not None
    repo.mark_failed(claimed, "boom")
    db_session.commit()
    assert claimed.status == ProcessingStatus.FAILED
    assert claimed.error_message == "boom"
