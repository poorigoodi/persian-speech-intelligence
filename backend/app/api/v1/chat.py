"""Grounded Q&A chat endpoint."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import AppSettings, DbSession, require_api_key
from app.core.exceptions import ConflictError, NotFoundError
from app.db.repositories import AnalysisRepository, RecordingRepository, TranscriptRepository
from app.llm.factory import get_llm_provider
from app.models.recording import ProcessingStatus
from app.retrieval.retriever import TranscriptRetriever
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.embedding_service import EmbeddingService
from app.services.qa_service import QAService
from app.services.recording_repair import ensure_recording_repaired
from app.utils.audio_metadata import get_recording_audio_metadata

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/{recording_id}/chat", response_model=ChatResponse)
async def chat(
    recording_id: UUID,
    body: ChatRequest,
    db: DbSession,
    settings: AppSettings,
) -> ChatResponse:
    recording = RecordingRepository(db).get(recording_id)
    if recording is None:
        raise NotFoundError("Recording not found.")
    if recording.processing_status != ProcessingStatus.COMPLETED:
        raise ConflictError("Recording has not finished processing yet.")

    ensure_recording_repaired(db, recording)
    audio_metadata = get_recording_audio_metadata(
        recording.storage_path, upload_dir=settings.upload_dir
    )
    analysis_row = AnalysisRepository(db).get_for_recording(recording_id)
    existing_analysis = (
        {
            "short_summary": analysis_row.short_summary,
            "extracted_entities": analysis_row.extracted_entities or {},
        }
        if analysis_row
        else None
    )

    segments = TranscriptRepository(db).list_for_recording(recording_id)
    if not segments and not audio_metadata.get("has_metadata"):
        return ChatResponse(
            recording_id=recording_id,
            question=body.question,
            answer="اطلاعات کافی برای پاسخ به این سؤال در فایل صوتی وجود ندارد.",
            grounded=False,
            evidence=[],
        )

    # Ensure index exists (safe no-op if already present)
    embedding_service = EmbeddingService(settings)
    if segments and not (settings.vector_index_dir / f"{recording_id}.faiss").exists():
        embedding_service.index_recording(recording_id, segments)

    llm = get_llm_provider(settings)
    qa = QAService(llm, retriever=TranscriptRetriever(settings, embedding_service))
    return await qa.answer(
        recording_id,
        body.question.strip(),
        audio_metadata=audio_metadata,
        existing_analysis=existing_analysis,
    )
