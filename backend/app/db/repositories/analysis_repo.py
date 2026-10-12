"""Analysis repository."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis


class AnalysisRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_recording(self, recording_id: UUID) -> Analysis | None:
        stmt = select(Analysis).where(Analysis.recording_id == recording_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert(
        self,
        recording_id: UUID,
        *,
        short_summary: str | None,
        detailed_summary: dict[str, Any] | None,
        topics: list[Any] | None,
        sentiment: dict[str, Any] | None,
        extracted_entities: dict[str, Any] | None,
        action_items: list[Any] | None,
        decisions: list[Any] | None,
    ) -> Analysis:
        analysis = self.get_for_recording(recording_id)
        if analysis is None:
            analysis = Analysis(recording_id=recording_id)
            self.db.add(analysis)

        analysis.short_summary = short_summary
        analysis.detailed_summary = detailed_summary
        analysis.topics = topics
        analysis.sentiment = sentiment
        analysis.extracted_entities = extracted_entities
        analysis.action_items = action_items
        analysis.decisions = decisions
        self.db.flush()
        return analysis

    def delete_for_recording(self, recording_id: UUID) -> None:
        analysis = self.get_for_recording(recording_id)
        if analysis is not None:
            self.db.delete(analysis)
            self.db.flush()
