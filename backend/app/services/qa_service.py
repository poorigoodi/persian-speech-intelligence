"""Grounded question answering over a single recording's transcript, audio metadata, and analysis."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.repositories import AnalysisRepository, RecordingRepository, TranscriptRepository
from app.db.session import SessionLocal
from app.llm.base import LLMMessage, LLMProvider
from app.retrieval.retriever import TranscriptRetriever
from app.schemas.chat import ChatResponse, EvidenceSegment
from app.services.persian_nlp_fallback import (
    answer_question_grounded,
    detect_question_language,
)
from app.utils.audio_metadata import get_recording_audio_metadata

logger = get_logger(__name__)

REFUSAL_FA = "اطلاعات کافی برای پاسخ به این سؤال در فایل صوتی وجود ندارد."
REFUSAL_EN = "There is not enough information in this recording's transcript to answer that question."

SYSTEM_PROMPT_FA = """شما دستیار پرسش‌وپاسخ مبتنی بر شواهد برای فایل‌های صوتی (فارسی و انگلیسی) هستید.
برای پاسخ به سؤالات، سه منبع اطلاعاتی در اختیار دارید:
۱. متادیتای فایل صوتی (Audio Metadata مانند خواننده/Artist، عنوان قطعه/Title، آلبوم/Album، آهنگساز/Composer)
۲. متن پیاده‌سازی‌شده (Transcript)
۳. نتایج تحلیل موجود (Analysis Results)
اگر کاربر دربارهٔ خواننده، هنرمند، نام آهنگ، آلبوم یا آهنگساز سؤال پرسید، ابتدا متادیتای فایل صوتی را بررسی کنید؛ در صورت نبود، متن گفتار را بررسی کنید و اگر در هیچ‌کدام نبود، به صورت شفاف اعلام کنید که این اطلاعات از روی فایل بارگذاری‌شده قابل تشخیص نیست.
هرگز نام خواننده، عنوان آهنگ یا آلبوم را حدس نزنید یا جعل نکنید.
پاسخ را حتماً به زبان فارسی بنویسید."""

SYSTEM_PROMPT_EN = """You are an evidence-grounded Q&A assistant for audio recordings (in Persian or English).
You have three information sources available:
1. Audio Metadata (verified ID3/container tags such as Artist, Title/Track Name, Album, Composer, Genre, Date)
2. Transcription (Transcript segments)
3. Existing Analysis Results (Summary and extracted entities)
When the user asks who the singer/artist/composer is, what the name of the song/track is, or which album it belongs to, check the Audio Metadata first, then the Transcription. If the information is unavailable in both, clearly state that it cannot be determined from the uploaded file.
Never invent or guess an artist name, song title, or album.
Write your response in English."""

_METADATA_PRIORITY_KEYWORDS = (
    "singer", "artist", "vocalist", "performer", "band", "musician",
    "who sings", "who sang", "sung by", "performed by",
    "composer", "songwriter", "wrote this song", "written by", "composed by",
    "album", "which album", "what album",
    "name of this song", "title of this song", "song name", "song title",
    "track name", "track title", "name of the song", "name of the track",
    "what song is this", "which song is this", "what track is this",
    "metadata", "id3", "release year", "release date",
    "خواننده", "هنرمند", "آرتیست", "اجراکننده", "کی خونده", "کی خوانده", "چه کسی خوانده",
    "آهنگساز", "آهنگ‌ساز", "ترانه‌سرا", "ترانه سرا",
    "آلبوم", "کدام آلبوم", "اسم آلبوم", "نام آلبوم",
    "اسم آهنگ", "نام آهنگ", "اسم این آهنگ", "نام این آهنگ", "اسم ترانه", "نام ترانه",
    "عنوان آهنگ", "عنوان قطعه", "اسم قطعه", "نام قطعه", "اسم موزیک", "متادیتا",
)


class QAService:
    def __init__(
        self,
        llm: LLMProvider,
        retriever: TranscriptRetriever | None = None,
    ) -> None:
        self.llm = llm
        self.retriever = retriever or TranscriptRetriever()

    async def answer(
        self,
        recording_id: UUID,
        question: str,
        *,
        audio_metadata: dict[str, Any] | None = None,
        existing_analysis: dict[str, Any] | None = None,
    ) -> ChatResponse:
        try:
            hits = self.retriever.retrieve(recording_id, question)
        except Exception as exc:
            logger.warning("FAISS retrieval fallback for %s: %s", recording_id, exc)
            hits = []

        evidence = [
            EvidenceSegment(
                segment_id=UUID(meta.segment_ids[0]) if meta.segment_ids else None,
                start_time=meta.start_time,
                end_time=meta.end_time,
                text=meta.text,
                score=score,
            )
            for meta, score in hits
        ]

        all_texts: list[str] = []
        db = SessionLocal()
        try:
            segs = TranscriptRepository(db).list_for_recording(recording_id)
            all_texts = [
                (s.normalized_text or s.original_text)
                for s in segs
                if (s.normalized_text or s.original_text or "").strip()
            ]
            if not evidence and segs:
                evidence = [
                    EvidenceSegment(
                        segment_id=s.id,
                        start_time=s.start_time,
                        end_time=s.end_time,
                        text=s.normalized_text or s.original_text,
                        score=1.0,
                    )
                    for s in segs
                    if (s.normalized_text or s.original_text).strip()
                ]
            if audio_metadata is None:
                rec = RecordingRepository(db).get(recording_id)
                if rec:
                    audio_metadata = get_recording_audio_metadata(rec.storage_path)
            if existing_analysis is None:
                analysis_row = AnalysisRepository(db).get_for_recording(recording_id)
                if analysis_row:
                    existing_analysis = {
                        "short_summary": analysis_row.short_summary,
                        "extracted_entities": analysis_row.extracted_entities or {},
                    }
        finally:
            db.close()

        if not all_texts and evidence:
            all_texts = [ev.text for ev in evidence if ev.text and ev.text.strip()]

        reply_lang = detect_question_language(question)
        reply_en = reply_lang == "en"
        refusal_msg = REFUSAL_EN if reply_en else REFUSAL_FA
        meta = audio_metadata or {}
        has_meta = bool(meta.get("has_metadata"))

        if not evidence and not has_meta:
            return ChatResponse(
                recording_id=recording_id,
                question=question,
                answer=refusal_msg,
                grounded=False,
                evidence=[],
            )

        q_lower = (question or "").lower()
        if any(k in q_lower for k in _METADATA_PRIORITY_KEYWORDS):
            answer, grounded = answer_question_grounded(
                question,
                all_texts,
                audio_metadata=meta,
                existing_analysis=existing_analysis,
            )
            return ChatResponse(
                recording_id=recording_id,
                question=question,
                answer=answer,
                grounded=grounded,
                evidence=evidence[:3],
            )

        context_blocks = []
        for i, ev in enumerate(evidence, start=1):
            context_blocks.append(
                f"[{i}] {ev.start_time:.1f}-{ev.end_time:.1f}s: {ev.text}"
            )
        context = "\n".join(context_blocks) if context_blocks else "(No transcript segments)"

        meta_block = "No embedded audio metadata tags found."
        if has_meta:
            meta_lines = [
                f"- {label}: {meta[key]}"
                for key, label in (
                    ("artist", "Artist/Singer"),
                    ("album_artist", "Album Artist"),
                    ("title", "Title/Track Name"),
                    ("album", "Album"),
                    ("composer", "Composer"),
                    ("genre", "Genre"),
                    ("date", "Release Date/Year"),
                    ("publisher", "Publisher/Label"),
                )
                if meta.get(key)
            ]
            if meta_lines:
                meta_block = "\n".join(meta_lines)

        analysis_block = ""
        if existing_analysis:
            ents = existing_analysis.get("extracted_entities") or {}
            people_str = ", ".join(ents.get("people") or []) or "None"
            orgs_str = ", ".join(ents.get("organizations") or []) or "None"
            summary_str = existing_analysis.get("short_summary") or ""
            analysis_block = f"People: {people_str}\nOrganizations: {orgs_str}\nSummary: {summary_str}"

        messages = [
            LLMMessage(
                role="system",
                content=SYSTEM_PROMPT_EN if reply_en else SYSTEM_PROMPT_FA,
            ),
            LLMMessage(
                role="user",
                content=(
                    f"User question:\n{question}\n\n"
                    f"Audio Metadata:\n{meta_block}\n\n"
                    f"Analysis Context:\n{analysis_block or 'N/A'}\n\n"
                    f"Transcript evidence:\n{context}\n\n"
                    "Provide a concise, grounded answer in English."
                    if reply_en
                    else f"سؤال کاربر:\n{question}\n\n"
                    f"متادیتای فایل صوتی:\n{meta_block}\n\n"
                    f"خلاصه تحلیل:\n{analysis_block or 'ندارد'}\n\n"
                    f"شواهد transcript:\n{context}\n\n"
                    "پاسخ کوتاه و مستند به زبان فارسی بدهید."
                ),
            ),
        ]
        try:
            response = await self.llm.chat(messages, temperature=0.1)
            answer = (response.content or "").strip() or refusal_msg
            grounded = (REFUSAL_FA not in answer) and (REFUSAL_EN not in answer)
            if not grounded:
                answer, grounded = answer_question_grounded(
                    question,
                    all_texts,
                    audio_metadata=meta,
                    existing_analysis=existing_analysis,
                )
        except Exception as exc:
            logger.warning(
                "External LLM unavailable for QA on %s (%s); using grounded local QA fallback.",
                recording_id,
                exc,
            )
            answer, grounded = answer_question_grounded(
                question,
                all_texts,
                audio_metadata=meta,
                existing_analysis=existing_analysis,
            )

        return ChatResponse(
            recording_id=recording_id,
            question=question,
            answer=answer,
            grounded=grounded,
            evidence=evidence,
        )
