"""Database-backed background worker for audio processing jobs."""

from __future__ import annotations

import asyncio
import signal
import time
import uuid
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.logging import get_logger, setup_logging
from app.db.repositories import (
    AnalysisRepository,
    JobRepository,
    RecordingRepository,
    TranscriptRepository,
)
from app.db.session import SessionLocal
from app.llm.factory import get_llm_provider
from app.models.recording import ProcessingStatus
from app.models.transcript import TranscriptSegment
from app.services.analysis_pipeline import AnalysisPipeline
from app.services.audio_service import AudioService
from app.services.embedding_service import EmbeddingService
from app.services.transcription_service import TranscriptionService

logger = get_logger(__name__)


class ProcessingWorker:
    """Polls for pending jobs and runs the ASR + analysis pipeline."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._stop = False
        self.audio_service = AudioService(self.settings)
        self.transcription_service = TranscriptionService(self.settings)
        self.embedding_service = EmbeddingService(self.settings)

    def request_stop(self, *_args) -> None:
        logger.info("Stop signal received; worker will exit after current job.")
        self._stop = True

    def run_forever(self) -> None:
        setup_logging(self.settings.log_level)
        logger.info(
            "Worker started (poll=%ss, concurrency=%s)",
            self.settings.worker_poll_interval_seconds,
            self.settings.worker_max_concurrency,
        )
        signal.signal(signal.SIGINT, self.request_stop)
        signal.signal(signal.SIGTERM, self.request_stop)

        while not self._stop:
            processed = self.poll_once()
            if not processed:
                time.sleep(self.settings.worker_poll_interval_seconds)

        logger.info("Worker stopped.")

    def poll_once(self) -> bool:
        db = SessionLocal()
        try:
            job_repo = JobRepository(db)
            job_repo.requeue_stale(self.settings.job_stale_timeout_seconds)
            db.commit()

            job = job_repo.claim_next_pending(max_retries=self.settings.worker_max_retries)
            if job is None:
                db.commit()
                return False
            db.commit()
            recording_id = job.recording_id
            job_id = job.id
        except Exception:
            db.rollback()
            logger.exception("Failed while claiming job")
            return False
        finally:
            db.close()

        try:
            asyncio.run(self.process_job(job_id, recording_id))
        except Exception:
            logger.exception("Unhandled error processing job %s", job_id)
        return True

    async def process_job(self, job_id: uuid.UUID, recording_id: uuid.UUID) -> None:
        db = SessionLocal()
        try:
            job_repo = JobRepository(db)
            recording_repo = RecordingRepository(db)
            transcript_repo = TranscriptRepository(db)
            analysis_repo = AnalysisRepository(db)

            job = job_repo.get(job_id)
            recording = recording_repo.get(recording_id)
            if job is None or recording is None:
                logger.error("Job or recording missing: %s / %s", job_id, recording_id)
                return

            recording_repo.update_status(recording, ProcessingStatus.PROCESSING)
            job_repo.update_progress(job, progress=5, current_step="preprocess")
            db.commit()

            source = Path(recording.storage_path)
            wav_path = self.audio_service.preprocess_for_asr(source, recording.id)

            job_repo.update_progress(job, progress=25, current_step="transcribe")
            db.commit()

            result = self.transcription_service.transcribe(wav_path)
            recording.language = result.language
            if result.duration_seconds:
                recording.duration_seconds = result.duration_seconds

            segments = [
                TranscriptSegment(
                    recording_id=recording.id,
                    segment_index=idx,
                    start_time=seg.start,
                    end_time=seg.end,
                    original_text=seg.text,
                    normalized_text=seg.normalized_text,
                    avg_logprob=seg.avg_logprob,
                    no_speech_prob=seg.no_speech_prob,
                )
                for idx, seg in enumerate(result.segments)
            ]
            transcript_repo.replace_segments(recording.id, segments)
            job_repo.update_progress(job, progress=55, current_step="embed")
            db.commit()

            # Refresh segments with IDs
            stored_segments = transcript_repo.list_for_recording(recording.id)
            self.embedding_service.index_recording(recording.id, stored_segments)

            job_repo.update_progress(job, progress=70, current_step="analyze")
            db.commit()

            transcript_text = " ".join(
                s.normalized_text for s in stored_segments if s.normalized_text
            ).strip()

            if transcript_text:
                llm = get_llm_provider(self.settings)
                pipeline = AnalysisPipeline(llm)
                bundle = await pipeline.run(transcript_text)
                payload = bundle.as_db_payload()
                analysis_repo.upsert(recording.id, **payload)
            else:
                analysis_repo.upsert(
                    recording.id,
                    short_summary="",
                    detailed_summary={
                        "main_discussion": "",
                        "important_points": [],
                        "decisions": [],
                        "action_items": [],
                        "open_questions": [],
                        "final_conclusions": [],
                    },
                    topics=[],
                    sentiment={
                        "label": "Uncertain",
                        "explanation": "هیچ گفتار قابل‌تشخیصی در فایل صوتی یافت نشد.",
                        "supporting_segment_ids": [],
                        "score": None,
                        "disclaimer": (
                            "Text-based sentiment of transcript language only."
                        ),
                    },
                    extracted_entities={
                        "people": [],
                        "organizations": [],
                        "dates": [],
                        "times": [],
                        "locations": [],
                        "tasks": [],
                        "decisions": [],
                        "deadlines": [],
                        "keywords": [],
                    },
                    action_items=[],
                    decisions=[],
                )

            job_repo.mark_completed(job)
            recording_repo.update_status(recording, ProcessingStatus.COMPLETED)
            db.commit()
            logger.info("Completed processing for recording %s", recording.id)
        except AppError as exc:
            db.rollback()
            self._fail_job(job_id, recording_id, exc.message)
        except Exception as exc:
            db.rollback()
            self._fail_job(job_id, recording_id, f"Unexpected processing failure: {exc}")
        finally:
            self.audio_service.cleanup_temp(recording_id)
            db.close()

    def _fail_job(
        self,
        job_id: uuid.UUID,
        recording_id: uuid.UUID,
        error_message: str,
    ) -> None:
        db = SessionLocal()
        try:
            job_repo = JobRepository(db)
            recording_repo = RecordingRepository(db)
            job = job_repo.get(job_id)
            recording = recording_repo.get(recording_id)

            can_retry = (
                job is not None
                and job.attempt_count <= self.settings.worker_max_retries
            )
            if can_retry and job is not None:
                job.status = ProcessingStatus.PENDING
                job.current_step = "retry_pending"
                job.error_message = error_message
                if recording is not None:
                    recording_repo.update_status(
                        recording, ProcessingStatus.PENDING, error_message=error_message
                    )
                logger.warning(
                    "Requeueing job %s after failure (attempt %s): %s",
                    job_id,
                    job.attempt_count,
                    error_message,
                )
            else:
                if job is not None:
                    job_repo.mark_failed(job, error_message)
                if recording is not None:
                    recording_repo.update_status(
                        recording, ProcessingStatus.FAILED, error_message=error_message
                    )
                logger.error("Job %s failed permanently: %s", job_id, error_message)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to persist job failure state")
        finally:
            db.close()


def main() -> None:
    worker = ProcessingWorker()
    worker.run_forever()


if __name__ == "__main__":
    main()
