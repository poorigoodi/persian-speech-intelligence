"""Analysis and export endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.api.deps import DbSession, require_api_key
from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.repositories import AnalysisRepository, RecordingRepository, TranscriptRepository
from app.schemas.analysis import AnalysisResponse, ExportResponse
from app.services.export_service import ExportService

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/{recording_id}/analysis", response_model=AnalysisResponse)
def get_analysis(recording_id: UUID, db: DbSession) -> AnalysisResponse:
    recording = RecordingRepository(db).get(recording_id)
    if recording is None:
        raise NotFoundError("Recording not found.")

    analysis = AnalysisRepository(db).get_for_recording(recording_id)
    if analysis is None:
        raise NotFoundError("Analysis not available yet.")

    return AnalysisResponse(
        recording_id=recording_id,
        short_summary=analysis.short_summary,
        detailed_summary=analysis.detailed_summary,
        topics=analysis.topics,
        sentiment=analysis.sentiment,
        extracted_entities=analysis.extracted_entities,
        action_items=analysis.action_items,
        decisions=analysis.decisions,
    )


@router.get("/{recording_id}/export")
def export_analysis(
    recording_id: UUID,
    db: DbSession,
    format: str = Query(default="json", pattern="^(json|txt|markdown)$"),
):
    recording = RecordingRepository(db).get(recording_id)
    if recording is None:
        raise NotFoundError("Recording not found.")

    segments = TranscriptRepository(db).list_for_recording(recording_id)
    analysis = AnalysisRepository(db).get_for_recording(recording_id)

    try:
        result: ExportResponse = ExportService().export(
            recording, segments, analysis, fmt=format
        )
    except ValueError as exc:
        raise ValidationAppError(str(exc)) from exc

    media_types = {
        "json": "application/json; charset=utf-8",
        "txt": "text/plain; charset=utf-8",
        "markdown": "text/markdown; charset=utf-8",
    }
    return PlainTextResponse(
        content=result.content,
        media_type=media_types[result.format],
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
        },
    )
