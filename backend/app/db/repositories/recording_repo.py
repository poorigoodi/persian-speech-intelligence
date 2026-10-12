"""Recording repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.recording import ProcessingStatus, Recording


class RecordingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, recording: Recording) -> Recording:
        self.db.add(recording)
        self.db.flush()
        return recording

    def get(self, recording_id: UUID) -> Recording | None:
        return self.db.get(Recording, recording_id)

    def get_with_relations(self, recording_id: UUID) -> Recording | None:
        stmt = (
            select(Recording)
            .where(Recording.id == recording_id)
            .options(
                selectinload(Recording.segments),
                selectinload(Recording.analysis),
                selectinload(Recording.jobs),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: ProcessingStatus | None = None,
    ) -> tuple[list[Recording], int]:
        filters = []
        if status is not None:
            filters.append(Recording.processing_status == status)

        count_stmt = select(func.count()).select_from(Recording)
        list_stmt = select(Recording).order_by(Recording.created_at.desc())

        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)

        total = int(self.db.execute(count_stmt).scalar_one())
        items = list(self.db.execute(list_stmt.limit(limit).offset(offset)).scalars())
        return items, total

    def update_status(
        self,
        recording: Recording,
        status: ProcessingStatus,
        *,
        error_message: str | None = None,
    ) -> Recording:
        recording.processing_status = status
        recording.error_message = error_message
        self.db.flush()
        return recording

    def delete(self, recording: Recording) -> None:
        self.db.delete(recording)
        self.db.flush()

    def stats(self) -> dict[str, int]:
        rows = self.db.execute(
            select(Recording.processing_status, func.count())
            .group_by(Recording.processing_status)
        ).all()
        counts = {status.value: 0 for status in ProcessingStatus}
        total = 0
        for status, count in rows:
            key = status.value if isinstance(status, ProcessingStatus) else str(status)
            counts[key] = int(count)
            total += int(count)
        return {
            "total_recordings": total,
            "completed": counts.get("completed", 0),
            "processing": counts.get("processing", 0),
            "pending": counts.get("pending", 0),
            "failed": counts.get("failed", 0),
        }
