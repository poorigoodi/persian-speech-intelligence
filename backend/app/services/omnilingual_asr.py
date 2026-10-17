"""Meta Omnilingual ASR (medium = omniASR_LLM_1B_v2) backend.

Note: k2-fsa OmniVoice is TTS-only. This module uses facebookresearch/omnilingual-asr.
"""

from __future__ import annotations

import threading
from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import ProcessingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class OmnilingualAsrManager:
    """Load Omnilingual ASRInferencePipeline once per process."""

    _lock = threading.Lock()
    _instance: OmnilingualAsrManager | None = None

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._pipeline = None
        self._card: str | None = None

    @classmethod
    def get_instance(cls, settings: Settings) -> OmnilingualAsrManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(settings)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def get_pipeline(self):
        card = self.settings.omnilingual_model_card
        if self._pipeline is None or self._card != card:
            with self._lock:
                if self._pipeline is None or self._card != card:
                    self._pipeline = self._load(card)
                    self._card = card
        return self._pipeline

    def _load(self, card: str):
        try:
            from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline
        except ImportError as exc:
            raise ProcessingError(
                "omnilingual-asr is not installed. "
                "Install with: pip install omnilingual-asr",
                code="omnilingual_missing",
            ) from exc

        logger.info("Loading Omnilingual ASR model_card=%s", card)
        try:
            return ASRInferencePipeline(model_card=card)
        except Exception as exc:
            raise ProcessingError(f"Failed to load Omnilingual ASR: {exc}") from exc


def transcribe_file(
    audio_path: Path,
    settings: Settings,
    *,
    manager: OmnilingualAsrManager | None = None,
) -> tuple[str, float]:
    """Return (transcript_text, duration_seconds)."""
    if not audio_path.exists():
        raise ProcessingError(f"Audio file not found: {audio_path}")

    duration = _probe_duration(audio_path)
    mgr = manager or OmnilingualAsrManager.get_instance(settings)
    pipeline = mgr.get_pipeline()

    lang = settings.omnilingual_lang
    try:
        texts = pipeline.transcribe(
            [str(audio_path)],
            lang=[lang],
            batch_size=1,
        )
    except TypeError:
        # Some builds use different signature without lang=
        logger.warning("Omnilingual transcribe without lang= (compat mode)")
        texts = pipeline.transcribe([str(audio_path)], batch_size=1)
    except Exception as exc:
        raise ProcessingError(f"Omnilingual ASR failed: {exc}") from exc

    if not texts:
        return "", duration
    text = (texts[0] or "").strip() if isinstance(texts[0], str) else str(texts[0]).strip()
    return text, duration


def _probe_duration(path: Path) -> float:
    try:
        import soundfile as sf

        info = sf.info(str(path))
        return float(info.duration or 0.0)
    except Exception:
        try:
            from app.utils.ffmpeg import extract_audio_info, probe_audio

            return float(extract_audio_info(probe_audio(path))["duration"])
        except Exception:
            return 0.0
