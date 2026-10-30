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
from app.services.persian_nlp_fallback import (
    ANALYSIS_SOURCE,
    build_smart_analysis,
    emotions_for_text,
)

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/{recording_id}/analysis", response_model=AnalysisResponse)
def get_analysis(recording_id: UUID, db: DbSession) -> AnalysisResponse:
    recording = RecordingRepository(db).get(recording_id)
    if recording is None:
        raise NotFoundError("Recording not found.")

    analysis_repo = AnalysisRepository(db)
    analysis = analysis_repo.get_for_recording(recording_id)
    if analysis is None:
        raise NotFoundError("Analysis not available yet.")

    sentiment_dict = analysis.sentiment if isinstance(analysis.sentiment, dict) else {}
    source = str(sentiment_dict.get("source") or "")
    explanation = str(sentiment_dict.get("explanation", ""))
    legacy_local_markers = (
        "سرویس LLM محلی",
        "لحن گفتار مثبت، شفاف",
        "لحن کلی گفتار متعادل، خبری و آموزشی است",
        "در متن گفتار به چالش‌ها",
    )
    is_legacy_local = (not source and any(m in explanation for m in legacy_local_markers)) or (
        source.startswith("local_nlp") and source != ANALYSIS_SOURCE
    )
    needs_emotions = not isinstance(sentiment_dict.get("emotions"), dict)

    if is_legacy_local or needs_emotions:
        segments = TranscriptRepository(db).list_for_recording(recording_id)
        seg_texts = [
            s.normalized_text or s.original_text
            for s in segments
            if (s.normalized_text or s.original_text)
        ]
        transcript_text = " ".join(seg_texts).strip()
        if transcript_text:
            if is_legacy_local:
                payload = build_smart_analysis(transcript_text, seg_texts)
                analysis = analysis_repo.upsert(recording_id, **payload)
            else:
                # Real LLM analysis: keep it, only attach measured emotions/language.
                enriched = {**sentiment_dict, **emotions_for_text(transcript_text, seg_texts)}
                analysis.sentiment = enriched
                db.flush()
            db.commit()

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
