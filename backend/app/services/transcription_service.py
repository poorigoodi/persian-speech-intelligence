"""Persian ASR using faster-whisper with reusable model loading."""

from __future__ import annotations

import ctypes
import os
import re
import site
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.exceptions import ProcessingError
from app.core.logging import get_logger
from app.utils.asr_correct import apply_asr_rules
from app.utils.persian_normalize import normalize_persian_text

logger = get_logger(__name__)


def _register_nvidia_dll_dirs() -> None:
    """Register pip-installed nvidia-cublas-cu12 / nvidia-cudnn-cu12 bin folders on Windows."""
    if sys.platform != "win32":
        return
    candidates: list[Path] = []
    for base in site.getsitepackages() + [site.getusersitepackages()]:
        if not base:
            continue
        nvidia_root = Path(base) / "nvidia"
        if nvidia_root.is_dir():
            for bin_dir in nvidia_root.glob("*/bin"):
                if bin_dir.is_dir():
                    candidates.append(bin_dir)
    if not candidates:
        return
    current_path = os.environ.get("PATH", "")
    path_parts = current_path.split(os.pathsep) if current_path else []
    for bin_dir in candidates:
        dir_str = str(bin_dir.resolve())
        if dir_str not in path_parts:
            path_parts.insert(0, dir_str)
        try:
            os.add_dll_directory(dir_str)
        except Exception:
            pass
    os.environ["PATH"] = os.pathsep.join(path_parts)


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
    language_probability: float | None = None

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
        self._loaded_key: tuple[str, str, str] | None = None

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
        key = (
            self.settings.whisper_model,
            self.settings.whisper_device,
            self.settings.whisper_compute_type,
        )
        if self._model is None or self._loaded_key != key:
            with self._lock:
                if self._model is None or self._loaded_key != key:
                    self._model = self._load_model()
                    self._loaded_key = key
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
        model_id = self.settings.whisper_model

        if device == "cuda" and sys.platform == "win32":
            _register_nvidia_dll_dirs()
            try:
                ctypes.WinDLL("cublas64_12.dll")
            except OSError:
                logger.warning(
                    "CUDA library cublas64_12.dll not found on Windows (run 'pip install nvidia-cublas-cu12 nvidia-cudnn-cu12' to enable GPU); falling back to CPU (int8)."
                )
                device = "cpu"
                compute_type = "int8"

        logger.info(
            "Loading Whisper model '%s' on %s (%s)",
            model_id,
            device,
            compute_type,
        )

        def _instantiate(name: str, dev: str, ctype: str):
            try:
                return WhisperModel(
                    name,
                    device=dev,
                    compute_type=ctype,
                    local_files_only=True,
                )
            except Exception:
                return WhisperModel(
                    name,
                    device=dev,
                    compute_type=ctype,
                )

        try:
            return _instantiate(model_id, device, compute_type)
        except Exception as exc:
            err_text = str(exc).lower()
            is_network_err = any(
                token in err_text
                for token in ("ssl", "connection", "maxretryerror", "network", "eof", "huggingface")
            )
            if is_network_err and model_id != "medium":
                logger.warning(
                    "Whisper model '%s' download failed (%s); falling back to locally cached 'medium' model.",
                    model_id,
                    exc,
                )
                try:
                    return WhisperModel(
                        "medium",
                        device=device,
                        compute_type=compute_type,
                        local_files_only=True,
                    )
                except Exception:
                    pass

            # Fallback to CPU if CUDA init fails
            if device != "cpu" and not is_network_err:
                logger.warning("Whisper CUDA load failed (%s); falling back to CPU.", exc)
                return _instantiate(model_id, "cpu", "int8")
            raise ProcessingError(f"Failed to load Whisper model: {exc}") from exc


class TranscriptionService:
    """Transcribe Persian audio with faster-whisper."""

    def __init__(
        self,
        settings: Settings | None = None,
        model_manager: WhisperModelManager | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.model_manager = model_manager or WhisperModelManager.get_instance(
            self.settings
        )

    # Languages Whisper often confuses with Persian on short / noisy clips.
    _PERSIAN_LOOKALIKES = {"ar", "ur", "ps", "tg"}

    def _base_kwargs(self) -> dict:
        return {
            "task": "transcribe",
            "beam_size": self.settings.whisper_beam_size,
            "best_of": self.settings.whisper_best_of,
            "patience": self.settings.whisper_patience,
            "temperature": self.settings.whisper_temperature,
            "vad_filter": self.settings.whisper_vad_filter,
            "word_timestamps": False,
            "condition_on_previous_text": self.settings.whisper_condition_on_previous_text,
            "compression_ratio_threshold": 2.4,
            "log_prob_threshold": -1.0,
            "no_speech_threshold": 0.6,
        }

    def _run(self, model, audio_path: Path, kwargs: dict):
        try:
            return model.transcribe(str(audio_path), **kwargs)
        except TypeError:
            # Older faster-whisper without hotwords/patience — retry leaner kwargs.
            lean = {
                k: v
                for k, v in kwargs.items()
                if k not in {"hotwords", "patience", "best_of", "condition_on_previous_text"}
            }
            logger.warning("Retrying Whisper transcribe with compatibility kwargs.")
            return model.transcribe(str(audio_path), **lean)

    def _detect_language(self, model, audio_path: Path) -> tuple[str, float]:
        """Detect the spoken language WITHOUT any Persian prompt bias."""
        forced = (self.settings.whisper_language or "").strip() or None
        if not self.settings.whisper_auto_detect_language and forced:
            return forced, 1.0
        try:
            _segments, info = self._run(
                model,
                audio_path,
                {**self._base_kwargs(), "language": None, "beam_size": 1, "best_of": 1},
            )
            lang = (getattr(info, "language", None) or forced or "en").lower()
            prob = float(getattr(info, "language_probability", 0.0) or 0.0)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Language detection failed (%s); using default.", exc)
            return forced or "fa", 0.0

        if lang in self._PERSIAN_LOOKALIKES and forced == "fa" and prob < 0.85:
            logger.info("Detected '%s' (p=%.2f) treated as Persian.", lang, prob)
            lang = "fa"
        logger.info("Detected spoken language: %s (p=%.2f)", lang, prob)
        return lang, prob

    @staticmethod
    def _is_prompt_echo(text: str, prompt_texts: list[str]) -> bool:
        """Whisper sometimes hallucinates the initial prompt itself on music/silence."""
        compact = re.sub(r"[\s\u200c.,،!?؟:؛\-]+", "", text)
        if not compact:
            return True
        for ref in prompt_texts:
            ref_compact = re.sub(r"[\s\u200c.,،!?؟:؛\-]+", "", ref)
            if ref_compact and compact in ref_compact:
                return True
        return False

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        if not audio_path.exists():
            raise ProcessingError(f"Audio file not found for transcription: {audio_path}")

        model = self.model_manager.get_model()
        language, language_prob = self._detect_language(model, audio_path)
        is_persian = language == "fa"

        kwargs = {**self._base_kwargs(), "language": language}
        prompt = (self.settings.whisper_initial_prompt or "").strip()
        hotwords = (self.settings.whisper_hotwords or "").strip()
        # Persian vocabulary prompt/hotwords only make sense for Persian audio;
        # on English songs/speech they cause the model to hallucinate the prompt.
        if is_persian:
            if prompt:
                kwargs["initial_prompt"] = prompt
            if hotwords:
                kwargs["hotwords"] = hotwords

        try:
            segments_iter, info = self._run(model, audio_path, kwargs)
            raw_segments = list(segments_iter)
        except Exception as exc:
            err_lower = str(exc).lower()
            if not any(tok in err_lower for tok in ("cublas", "cudnn", "cuda")):
                raise ProcessingError(f"ASR transcription failed: {exc}") from exc
            logger.warning(
                "CUDA runtime error during Whisper transcription (%s); retrying on CPU (int8).",
                exc,
            )
            from faster_whisper import WhisperModel

            try:
                cpu_model = WhisperModel(
                    self.settings.whisper_model,
                    device="cpu",
                    compute_type="int8",
                    local_files_only=True,
                )
            except Exception:
                cpu_model = WhisperModel(
                    self.settings.whisper_model, device="cpu", compute_type="int8"
                )
            self.model_manager._model = cpu_model
            segments_iter, info = self._run(cpu_model, audio_path, kwargs)
            raw_segments = list(segments_iter)

        prompt_texts = [t for t in (prompt, hotwords) if t]
        segments: list[TranscriptSegmentResult] = []
        dropped = 0
        for seg in raw_segments:
            text = (seg.text or "").strip()
            if not text:
                continue
            avg_lp = getattr(seg, "avg_logprob", None)
            no_sp = getattr(seg, "no_speech_prob", None)
            if is_persian and self._is_prompt_echo(text, prompt_texts):
                dropped += 1
                continue
            if no_sp is not None and avg_lp is not None and no_sp > 0.6 and avg_lp < -1.0:
                dropped += 1
                continue
            cleaned = apply_asr_rules(text) if is_persian else text
            segments.append(
                TranscriptSegmentResult(
                    start=float(seg.start or 0.0),
                    end=float(seg.end or 0.0),
                    text=cleaned,
                    normalized_text=normalize_persian_text(cleaned) if is_persian else cleaned,
                    avg_logprob=avg_lp,
                    no_speech_prob=no_sp,
                )
            )

        if dropped:
            logger.info("Dropped %s hallucinated/low-confidence segments.", dropped)
        duration = float(getattr(info, "duration", 0.0) or 0.0)
        if not segments:
            logger.info("Transcription produced no speech segments (possibly silent audio).")

        return TranscriptionResult(
            language=language,
            duration_seconds=duration,
            segments=segments,
            language_probability=language_prob,
        )
