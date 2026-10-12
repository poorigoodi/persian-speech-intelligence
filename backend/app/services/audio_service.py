"""Audio upload validation and preprocessing."""

from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import AudioValidationError
from app.core.logging import get_logger
from app.utils.ffmpeg import convert_to_wav_mono_16k, extract_audio_info, probe_audio
from app.utils.files import SAFE_AUDIO_EXTENSIONS, generate_storage_filename, sanitize_filename

logger = get_logger(__name__)

# Magic-byte signatures for basic content validation (not relying on client MIME)
_SIGNATURES: list[tuple[bytes, str]] = [
    (b"RIFF", "wav"),
    (b"ID3", "mp3"),
    (b"\xff\xfb", "mp3"),
    (b"\xff\xf3", "mp3"),
    (b"\xff\xf2", "mp3"),
    (b"fLaC", "flac"),
    (b"OggS", "ogg"),
    # M4A / MP4 often start with ftyp at offset 4
]


class AudioService:
    """Validate, store, and preprocess uploaded audio files."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def save_upload(self, upload: UploadFile) -> dict:
        """Validate and persist an uploaded audio file.

        Returns metadata including storage path (relative name only for API safety).
        """
        if not upload.filename:
            raise AudioValidationError("Filename is required.")

        original = sanitize_filename(upload.filename)
        ext = Path(original).suffix.lower()
        if ext not in SAFE_AUDIO_EXTENSIONS:
            raise AudioValidationError(
                f"Unsupported file extension '{ext}'. "
                f"Allowed: {', '.join(sorted(SAFE_AUDIO_EXTENSIONS))}"
            )

        storage_name = generate_storage_filename(original)
        destination = self.settings.upload_dir / storage_name

        size = 0
        max_bytes = self.settings.max_upload_bytes
        header = b""

        try:
            async with aiofiles.open(destination, "wb") as out:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    if len(header) < 32:
                        header += chunk[: 32 - len(header)]
                    size += len(chunk)
                    if size > max_bytes:
                        raise AudioValidationError(
                            f"File exceeds maximum upload size of {self.settings.max_upload_mb} MB."
                        )
                    await out.write(chunk)
        except Exception:
            if destination.exists():
                destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

        if size == 0:
            destination.unlink(missing_ok=True)
            raise AudioValidationError("Uploaded file is empty.")

        self._validate_magic_bytes(header, ext)
        info = self.validate_stored_file(destination)

        return {
            "original_filename": original,
            "storage_path": str(destination),
            "storage_name": storage_name,
            "file_size_bytes": size,
            "duration_seconds": info["duration"],
            "sample_rate": info["sample_rate"],
            "content_type": upload.content_type,
        }

    def _validate_magic_bytes(self, header: bytes, ext: str) -> None:
        """Lightweight content sniffing; FFmpeg remains the authoritative validator."""
        if ext == ".m4a":
            if b"ftyp" not in header[:32]:
                # Still allow; some valid m4a variants differ — FFmpeg will decide.
                logger.debug("M4A magic check inconclusive; deferring to FFmpeg.")
            return

        matched = any(header.startswith(sig) for sig, _ in _SIGNATURES)
        if not matched and ext == ".mp3":
            # MPEG frame sync without ID3
            matched = len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0

        if not matched:
            logger.warning("Audio magic-byte check failed for extension %s", ext)
            # Defer hard rejection to FFmpeg probe for robustness with rare containers.

    def validate_stored_file(self, path: Path) -> dict:
        """Probe and validate duration/format constraints."""
        probe = probe_audio(path)
        info = extract_audio_info(probe)

        duration = float(info["duration"])
        if duration < self.settings.min_audio_duration_seconds:
            path.unlink(missing_ok=True)
            raise AudioValidationError(
                f"Audio is too short ({duration:.2f}s). "
                f"Minimum is {self.settings.min_audio_duration_seconds}s."
            )
        if duration > self.settings.max_audio_duration_seconds:
            path.unlink(missing_ok=True)
            raise AudioValidationError(
                f"Audio exceeds maximum duration of "
                f"{self.settings.max_audio_duration_seconds}s."
            )
        return info

    def preprocess_for_asr(self, source: Path, recording_id: uuid.UUID) -> Path:
        """Convert audio to mono 16 kHz WAV in the temp directory."""
        dest = self.settings.temp_dir / f"{recording_id}_16k_mono.wav"
        return convert_to_wav_mono_16k(source, dest)

    def cleanup_temp(self, recording_id: uuid.UUID) -> None:
        pattern = f"{recording_id}_*"
        for path in self.settings.temp_dir.glob(pattern):
            path.unlink(missing_ok=True)

    def delete_storage_file(self, storage_path: str) -> None:
        path = Path(storage_path)
        try:
            resolved = path.resolve()
            upload_root = self.settings.upload_dir.resolve()
            if str(resolved).startswith(str(upload_root)) and resolved.exists():
                resolved.unlink()
        except OSError as exc:
            logger.warning("Failed to delete storage file: %s", exc)
