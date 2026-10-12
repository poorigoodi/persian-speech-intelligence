"""Safe file handling utilities."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

SAFE_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}

_UNSAFE_NAME = re.compile(r"[^\w.\-]+", re.UNICODE)


def sanitize_filename(filename: str) -> str:
    """Return a filesystem-safe basename without path components."""
    name = Path(filename).name
    name = name.replace("..", ".")
    name = _UNSAFE_NAME.sub("_", name).strip("._")
    if not name:
        name = "audio"
    return name[:200]


def generate_storage_filename(original_filename: str) -> str:
    """Generate a UUID-prefixed safe storage filename."""
    safe = sanitize_filename(original_filename)
    ext = Path(safe).suffix.lower()
    if ext not in SAFE_AUDIO_EXTENSIONS:
        ext = ".bin"
    stem = Path(safe).stem[:80] or "audio"
    return f"{uuid.uuid4()}_{stem}{ext}"


def resolve_under_directory(base_dir: Path, relative_path: str | Path) -> Path:
    """Resolve a path and ensure it stays under base_dir (path traversal protection)."""
    base = base_dir.resolve()
    target = (base / relative_path).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("Path traversal detected.")
    return target
