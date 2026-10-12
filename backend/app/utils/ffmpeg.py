"""FFmpeg helpers for audio validation and conversion."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from app.core.exceptions import AudioValidationError, ProcessingError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Resource limits for FFmpeg/ffprobe subprocesses
_DEFAULT_TIMEOUT = 120
_FFMPEG_THREADS = "2"


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise ProcessingError(
            "FFmpeg/ffprobe is not installed or not on PATH.",
            code="ffmpeg_missing",
        )


def probe_audio(path: Path, *, timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Probe audio metadata with ffprobe. Raises AudioValidationError on failure."""
    ensure_ffmpeg_available()
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioValidationError("Audio probe timed out.") from exc

    if result.returncode != 0:
        raise AudioValidationError(
            "Unable to probe audio file. The file may be corrupted or unsupported.",
            details={"stderr": (result.stderr or "")[:500]},
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AudioValidationError("Invalid ffprobe output.") from exc


def extract_audio_info(probe: dict) -> dict:
    """Extract duration, sample rate, channels from ffprobe JSON."""
    streams = probe.get("streams") or []
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    if not audio_streams:
        raise AudioValidationError("No audio stream found in uploaded file.")

    stream = audio_streams[0]
    fmt = probe.get("format") or {}

    try:
        duration = float(fmt.get("duration") or stream.get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0

    try:
        sample_rate = int(stream.get("sample_rate") or 0)
    except (TypeError, ValueError):
        sample_rate = 0

    try:
        channels = int(stream.get("channels") or 0)
    except (TypeError, ValueError):
        channels = 0

    return {
        "duration": duration,
        "sample_rate": sample_rate,
        "channels": channels,
        "codec": stream.get("codec_name"),
        "format_name": fmt.get("format_name"),
    }


def convert_to_wav_mono_16k(
    source: Path,
    destination: Path,
    *,
    timeout: int = _DEFAULT_TIMEOUT,
) -> Path:
    """Convert audio to mono 16 kHz PCM WAV for ASR."""
    ensure_ffmpeg_available()
    destination.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-threads",
        _FFMPEG_THREADS,
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProcessingError("Audio conversion timed out.") from exc

    if result.returncode != 0 or not destination.exists():
        raise ProcessingError(
            "Failed to convert audio for transcription.",
            details={"stderr": (result.stderr or "")[:500]},
        )
    return destination
