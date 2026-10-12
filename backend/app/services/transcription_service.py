"""Persian ASR using faster-whisper with reusable model loading."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.exceptions import ProcessingError
from app.core.logging import get_logger
from app.utils.persian_normalize import normalize_persian_text

logger = get_logger(__name__)


@dataclass
class TranscriptSegmentResult:
    start: float
    end: float
    text: str
    normalized_text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None


@dataclass
class TranscriptionResult:
    language: str
    duration_seconds: float
    segments: list[TranscriptSegmentResult] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return " ".join(s.text for s in self.segments if s.text.strip()).strip()

    @property
    def full_text_normalized(self) -> str:
        return " ".join(
            s.normalized_text for s in self.segments if s.normalized_text.strip()
        ).strip()


class WhisperModelManager:
    """Singleton-style manager that loads the Whisper model once per process."""

    _lock = threading.Lock()
    _instance: WhisperModelManager | None = None

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = None

    @classmethod
    def get_instance(cls, settings: Settings | None = None) -> WhisperModelManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(settings or get_settings())
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._model = self._load_model()
        return self._model

    def _load_model(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ProcessingError(
                "faster-whisper is not installed.",
                code="whisper_missing",
            ) from exc

        device = self.settings.whisper_device
        compute_type = self.settings.whisper_compute_type
        logger.info(
            "Loading Whisper model '%s' on %s (%s)",
            self.settings.whisper_model,
            device,
            compute_type,
        )
        try:
            return WhisperModel(
                self.settings.whisper_model,
                device=device,
                compute_type=compute_type,
            )
        except Exception as exc:
            # Fallback to CPU if CUDA init fails
            if device != "cpu":
                logger.warning("Whisper CUDA load failed (%s); falling back to CPU.", exc)
                return WhisperModel(
                    self.settings.whisper_model,
                    device="cpu",
                    compute_type="int8",
                )
            raise ProcessingError(f"Failed to load Whisper model: {exc}") from exc


class TranscriptionService:
    """Transcribe Persian audio with faster-whisper."""

    def __init__(
        self,
        settings: Settings | None = None,
        model_manager: WhisperModelManager | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.model_manager = model_manager or WhisperModelManager.get_instance(self.settings)

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        if not audio_path.exists():
            raise ProcessingError(f"Audio file not found for transcription: {audio_path}")

        model = self.model_manager.get_model()
        language = None if self.settings.whisper_auto_detect_language else self.settings.whisper_language

        try:
            segments_iter, info = model.transcribe(
                str(audio_path),
                language=language,
                beam_size=self.settings.whisper_beam_size,
                vad_filter=True,
                word_timestamps=False,
            )
        except Exception as exc:
            raise ProcessingError(f"ASR transcription failed: {exc}") from exc

        segments: list[TranscriptSegmentResult] = []
        for seg in segments_iter:
            text = (seg.text or "").strip()
            if not text:
                continue
            segments.append(
                TranscriptSegmentResult(
                    start=float(seg.start or 0.0),
                    end=float(seg.end or 0.0),
                    text=text,
                    normalized_text=normalize_persian_text(text),
                    avg_logprob=getattr(seg, "avg_logprob", None),
                    no_speech_prob=getattr(seg, "no_speech_prob", None),
                )
            )

        detected_language = getattr(info, "language", None) or self.settings.whisper_language
        duration = float(getattr(info, "duration", 0.0) or 0.0)

        if not segments:
            logger.info("Transcription produced no speech segments (possibly silent audio).")

        return TranscriptionResult(
            language=detected_language,
            duration_seconds=duration,
            segments=segments,
        )
