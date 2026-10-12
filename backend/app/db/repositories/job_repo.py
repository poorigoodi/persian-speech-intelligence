"""Processing job repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recording import ProcessingJob, ProcessingStatus


class JobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, job: ProcessingJob) -> ProcessingJob:
        self.db.add(job)
        self.db.flush()
        return job

    def get(self, job_id: UUID) -> ProcessingJob | None:
        return self.db.get(ProcessingJob, job_id)

    def get_latest_for_recording(self, recording_id: UUID) -> ProcessingJob | None:
        stmt = (
            select(ProcessingJob)
            .where(ProcessingJob.recording_id == recording_id)
            .order_by(ProcessingJob.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def claim_next_pending(self, *, max_retries: int) -> ProcessingJob | None:
        """Atomically claim the next pending job.

        Uses SKIP LOCKED on PostgreSQL. Falls back to a plain SELECT for SQLite/tests.
        """
        base = (
            select(ProcessingJob)
            .where(
                ProcessingJob.status == ProcessingStatus.PENDING,
                ProcessingJob.attempt_count <= max_retries,
            )
            .order_by(ProcessingJob.created_at.asc())
            .limit(1)
        )
        dialect = self.db.bind.dialect.name if self.db.bind is not None else ""
        stmt = base.with_for_update(skip_locked=True) if dialect == "postgresql" else base
        job = self.db.execute(stmt).scalar_one_or_none()
        if job is None:
            return None

        job.status = ProcessingStatus.PROCESSING
        job.attempt_count += 1
        job.started_at = datetime.now(UTC)
        job.progress = max(job.progress, 1)
        job.current_step = "claimed"
        job.error_message = None
        self.db.flush()
        return job

    def update_progress(
        self,
        job: ProcessingJob,
        *,
        progress: int,
        current_step: str,
    ) -> ProcessingJob:
        job.progress = max(0, min(100, progress))
        job.current_step = current_step
        self.db.flush()
        return job

    def mark_completed(self, job: ProcessingJob) -> ProcessingJob:
        job.status = ProcessingStatus.COMPLETED
        job.progress = 100
        job.current_step = "completed"
        job.completed_at = datetime.now(UTC)
        job.error_message = None
        self.db.flush()
        return job

    def mark_failed(self, job: ProcessingJob, error_message: str) -> ProcessingJob:
        job.status = ProcessingStatus.FAILED
        job.current_step = "failed"
        job.error_message = error_message
        job.completed_at = datetime.now(UTC)
        self.db.flush()
        return job

    def requeue_stale(self, stale_timeout_seconds: int) -> int:
        """Requeue jobs stuck in processing beyond the stale timeout."""
        cutoff = datetime.now(UTC) - timedelta(seconds=stale_timeout_seconds)
        stmt = select(ProcessingJob).where(
            ProcessingJob.status == ProcessingStatus.PROCESSING,
            ProcessingJob.started_at.is_not(None),
            ProcessingJob.started_at < cutoff,
        )
        jobs = list(self.db.execute(stmt).scalars())
        for job in jobs:
            job.status = ProcessingStatus.PENDING
            job.current_step = "requeued_stale"
            job.error_message = "Job was stale and requeued after worker restart/timeout."
        self.db.flush()
        return len(jobs)
