"""Grounded Q&A chat endpoint."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import AppSettings, DbSession, require_api_key
from app.core.exceptions import ConflictError, NotFoundError
from app.db.repositories import RecordingRepository, TranscriptRepository
from app.llm.factory import get_llm_provider
from app.models.recording import ProcessingStatus
from app.retrieval.retriever import TranscriptRetriever
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.embedding_service import EmbeddingService
from app.services.qa_service import QAService

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

    segments = TranscriptRepository(db).list_for_recording(recording_id)
    if not segments:
        return ChatResponse(
            recording_id=recording_id,
            question=body.question,
            answer="اطلاعات کافی برای پاسخ به این سؤال در فایل صوتی وجود ندارد.",
            grounded=False,
            evidence=[],
        )

    # Ensure index exists (safe no-op if already present)
    embedding_service = EmbeddingService(settings)
    if not (settings.vector_index_dir / f"{recording_id}.faiss").exists():
        embedding_service.index_recording(recording_id, segments)

    llm = get_llm_provider(settings)
    qa = QAService(llm, retriever=TranscriptRetriever(settings, embedding_service))
    return await qa.answer(recording_id, body.question.strip())
