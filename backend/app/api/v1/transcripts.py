"""Transcript retrieval endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_api_key
from app.core.exceptions import NotFoundError
from app.db.repositories import RecordingRepository, TranscriptRepository
from app.schemas.transcript import TranscriptResponse, TranscriptSegmentOut
from app.utils.asr_correct import apply_asr_rules

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/{recording_id}/transcript", response_model=TranscriptResponse)
def get_transcript(recording_id: UUID, db: DbSession) -> TranscriptResponse:
    recording = RecordingRepository(db).get(recording_id)
    if recording is None:
        raise NotFoundError("Recording not found.")

    segments = TranscriptRepository(db).list_for_recording(recording_id)
    updated = False
    for s in segments:
        cleaned_orig = apply_asr_rules(s.original_text)
        cleaned_norm = apply_asr_rules(s.normalized_text)
        if cleaned_orig != s.original_text or cleaned_norm != s.normalized_text:
            s.original_text = cleaned_orig
            s.normalized_text = cleaned_norm
            updated = True
    if updated:
        db.commit()

    full_text = " ".join(s.original_text for s in segments).strip()
    full_norm = " ".join(s.normalized_text for s in segments).strip()

    return TranscriptResponse(
        recording_id=recording_id,
        language=recording.language,
        duration_seconds=recording.duration_seconds,
        full_text=full_text,
        full_text_normalized=full_norm,
        segments=[TranscriptSegmentOut.model_validate(s) for s in segments],
    )
