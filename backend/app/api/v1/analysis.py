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
    detect_text_language,
    emotions_for_text,
    extract_locations,
    extract_organizations,
    extract_people,
)
from app.services.recording_repair import ensure_recording_repaired
from app.utils.audio_metadata import get_recording_audio_metadata

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/{recording_id}/analysis", response_model=AnalysisResponse)
def get_analysis(recording_id: UUID, db: DbSession) -> AnalysisResponse:
    recording = RecordingRepository(db).get(recording_id)
    if recording is None:
        raise NotFoundError("Recording not found.")

    ensure_recording_repaired(db, recording)
    analysis_repo = AnalysisRepository(db)
    analysis = analysis_repo.get_for_recording(recording_id)
    if analysis is None:
        raise NotFoundError("Analysis not available yet.")

    audio_meta = get_recording_audio_metadata(recording.storage_path)
    sentiment_dict = analysis.sentiment if isinstance(analysis.sentiment, dict) else {}
    source = str(sentiment_dict.get("source") or "")
    is_legacy_local = source != "llm" and source != ANALYSIS_SOURCE
    needs_emotions = not isinstance(sentiment_dict.get("emotions"), dict)
    entities_dict = (
        dict(analysis.extracted_entities)
        if isinstance(analysis.extracted_entities, dict)
        else {}
    )
    missing_meta_artist = bool(
        audio_meta.get("has_metadata")
        and audio_meta.get("artist")
        and not any(
            str(p).lower() == str(audio_meta["artist"]).lower()
            for p in (entities_dict.get("people") or [])
        )
    )

    if is_legacy_local or needs_emotions or missing_meta_artist:
        segments = TranscriptRepository(db).list_for_recording(recording_id)
        seg_texts = [
            s.normalized_text or s.original_text
            for s in segments
            if (s.normalized_text or s.original_text)
        ]
        transcript_text = " ".join(seg_texts).strip()
        if transcript_text:
            if is_legacy_local:
                payload = build_smart_analysis(
                    transcript_text, seg_texts, audio_metadata=audio_meta
                )
                analysis = analysis_repo.upsert(recording_id, **payload)
            else:
                # Real LLM analysis: keep it, attach measured emotions/language + verified entities/metadata.
                enriched = {**sentiment_dict, **emotions_for_text(transcript_text, seg_texts)}
                analysis.sentiment = enriched
                lang = detect_text_language(transcript_text)
                people = list(entities_dict.get("people") or [])
                orgs = list(entities_dict.get("organizations") or [])
                locs = list(entities_dict.get("locations") or [])
                for p in extract_people(transcript_text, lang):
                    if not any(str(existing).lower() == p.lower() for existing in people):
                        people.append(p)
                for o in extract_organizations(transcript_text):
                    if not any(str(existing).lower() == o.lower() for existing in orgs):
                        orgs.append(o)
                for loc in extract_locations(transcript_text):
                    if not any(str(existing).lower() == loc.lower() for existing in locs):
                        locs.append(loc)
                if audio_meta.get("has_metadata"):
                    for field_key in ("artist", "album_artist", "composer"):
                        val = (audio_meta.get(field_key) or "").strip()
                        if val and not any(str(existing).lower() == val.lower() for existing in people):
                            people.insert(0, val)
                    pub = (audio_meta.get("publisher") or "").strip()
                    if pub and not any(str(existing).lower() == pub.lower() for existing in orgs):
                        orgs.append(pub)
                entities_dict["people"] = people
                entities_dict["organizations"] = orgs
                entities_dict["locations"] = locs
                entities_dict["audio_metadata"] = audio_meta
                analysis.extracted_entities = entities_dict
                db.flush()
            db.commit()

    bilingual_insights = None
    if isinstance(analysis.detailed_summary, dict):
        bilingual_insights = analysis.detailed_summary.get("bilingual_insights")

    return AnalysisResponse(
        recording_id=recording_id,
        short_summary=analysis.short_summary,
        detailed_summary=analysis.detailed_summary,
        topics=analysis.topics,
        sentiment=analysis.sentiment,
        extracted_entities=analysis.extracted_entities,
        action_items=analysis.action_items,
        decisions=analysis.decisions,
        bilingual_insights=bilingual_insights,
        audio_metadata=audio_meta,
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

    ensure_recording_repaired(db, recording)
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
