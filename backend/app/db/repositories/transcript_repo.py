"""Transcript segment repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.transcript import TranscriptSegment


class TranscriptRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def replace_segments(
        self,
        recording_id: UUID,
        segments: list[TranscriptSegment],
    ) -> list[TranscriptSegment]:
        self.db.execute(
            delete(TranscriptSegment).where(TranscriptSegment.recording_id == recording_id)
        )
        for segment in segments:
            self.db.add(segment)
        self.db.flush()
        return segments

    def list_for_recording(self, recording_id: UUID) -> list[TranscriptSegment]:
        stmt = (
            select(TranscriptSegment)
            .where(TranscriptSegment.recording_id == recording_id)
            .order_by(TranscriptSegment.segment_index.asc())
        )
        return list(self.db.execute(stmt).scalars())

    def delete_for_recording(self, recording_id: UUID) -> None:
        self.db.execute(
            delete(TranscriptSegment).where(TranscriptSegment.recording_id == recording_id)
        )
        self.db.flush()
