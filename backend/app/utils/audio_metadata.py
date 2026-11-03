"""Extract verified audio metadata (ID3, iTunes MP4/M4A atoms, Vorbis/FLAC, RIFF WAV INFO).

Never infers or fabricates metadata from filenames. Handles missing, incomplete,
or corrupted files gracefully.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def resolve_audio_file_path(
    storage_path: str | Path | None,
    settings: Settings | None = None,
    upload_dir: str | Path | None = None,
) -> Path | None:
    """Resolve a recording's stored file path across repo/backend working directories."""
    if not storage_path:
        return None
    cfg = settings or get_settings()
    raw = Path(storage_path)
    file_dir = Path(__file__).parent
    backend_root = file_dir.parent.parent
    repo_root = backend_root.parent
    up_dir = Path(upload_dir) if upload_dir else cfg.upload_dir
    candidates = [
        raw,
        up_dir / raw.name,
        repo_root / "storage" / "uploads" / raw.name,
        backend_root / "storage" / "uploads" / raw.name,
        backend_root / raw,
        repo_root / raw,
    ]
    for candidate in candidates:
        try:
            if candidate.is_file():
                try:
                    return candidate.resolve()
                except Exception:
                    return candidate
        except Exception:
            continue
    return None


def get_recording_audio_metadata(
    storage_path: str | Path | None,
    settings: Settings | None = None,
    upload_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve a recording's audio file and extract its verified metadata."""
    resolved = resolve_audio_file_path(storage_path, settings=settings, upload_dir=upload_dir)
    return extract_audio_metadata(resolved)

# Patterns for watermark domains or technical encoder strings often injected by download sites
_DOMAIN_ONLY_RE = re.compile(
    r"^[\s\[\]()|_\-]*(?:https?://)?(?:www\.)?[a-z0-9\-]+\."
    r"(?:ir|net|com|org|me|io|co|info|biz|tv|fm|music)(?:/[^\s]*)?[\s\[\]()|_\-]*$",
    re.IGNORECASE,
)
_WATERMARK_PART_RE = re.compile(
    r"(?:\s*[\|¦/]\s*|\s+-\s+|\s*\[[^\]]*\]\s*|\s*\([^)]*\)\s*)"
    r"(?:https?://)?(?:www\.)?[a-z0-9\-]+\.(?:ir|net|com|org|me|io|co|info|fm)\b.*$",
    re.IGNORECASE,
)
_BRACKET_DOMAIN_RE = re.compile(
    r"[\[\(]\s*(?:https?://)?(?:www\.)?[a-z0-9\-]+\."
    r"(?:ir|net|com|org|me|io|co|info|fm)\s*[\]\)]",
    re.IGNORECASE,
)
_YOUTUBE_TOPIC_SUFFIX_RE = re.compile(r"\s*-\s*Topic\s*$", re.IGNORECASE)
_TECHNICAL_VALUES = {
    "cover",
    "cover (front)",
    "cover (back)",
    "other",
    "core media audio",
    "soundhandler",
    "iso media file",
    "unknown",
    "untitled",
    "track",
    "none",
    "null",
    "n/a",
    "und",
}
_ENCODER_PREFIXES = ("lavf", "lavc", "lame", "ffmpeg", "handbrake", "itun")


def _clean_tag_value(value: Any, *, is_artist: bool = False) -> str | None:
    """Clean a raw tag string, removing site watermarks and technical placeholders."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value if v is not None)
    text = str(value).replace("\x00", "").strip()
    if not text:
        return None

    # Ignore pure domain watermarks (e.g. "baarzesh.net" or "[ GOODMUSICS.IR ]")
    if _DOMAIN_ONLY_RE.match(text):
        return None

    # Strip bracketed domain watermarks and trailing "| domain.tld"
    text = _BRACKET_DOMAIN_RE.sub("", text).strip()
    text = _WATERMARK_PART_RE.sub("", text).strip()

    if is_artist:
        text = _YOUTUBE_TOPIC_SUFFIX_RE.sub("", text).strip()

    text = text.strip(" -|_/,;:")
    if not text:
        return None

    low = text.lower()
    if low in _TECHNICAL_VALUES:
        return None
    if low.startswith(_ENCODER_PREFIXES):
        return None
    if _DOMAIN_ONLY_RE.match(text):
        return None

    # Normalize ALL-CAPS Latin artist/title names ( of length >= 4 ) to readable Title Case
    if is_artist and text.isupper() and any(c.isalpha() for c in text) and len(text) >= 4:
        text = text.title()

    return text


def _read_raw_tags_av(path: Path) -> dict[str, str]:
    """Extract container and audio-stream tags via PyAV (libavformat)."""
    tags: dict[str, str] = {}
    try:
        import av

        with av.open(str(path)) as container:
            if container.metadata:
                for k, v in container.metadata.items():
                    if k and v and str(v).strip():
                        tags[str(k).strip()] = str(v).strip()
            for stream in container.streams:
                # Skip attached cover-art video streams (mjpeg/png)
                if getattr(stream, "type", None) != "audio":
                    continue
                if stream.metadata:
                    for k, v in stream.metadata.items():
                        if k and v and str(k).strip() not in tags and str(v).strip():
                            tags[str(k).strip()] = str(v).strip()
    except Exception as exc:
        logger.debug("PyAV tag read skipped for %s: %s", path.name, exc)
    return tags


def _read_raw_tags_ffprobe(path: Path) -> dict[str, str]:
    """Fallback tag extraction via ffprobe subprocess."""
    tags: dict[str, str] = {}
    try:
        from app.utils.ffmpeg import probe_audio

        data = probe_audio(path, timeout=15)
        fmt_tags = (data.get("format") or {}).get("tags") or {}
        for k, v in fmt_tags.items():
            if k and v and str(v).strip():
                tags[str(k).strip()] = str(v).strip()
        for stream in data.get("streams") or []:
            if stream.get("codec_type") != "audio":
                continue
            s_tags = stream.get("tags") or {}
            for k, v in s_tags.items():
                if k and v and str(k).strip() not in tags and str(v).strip():
                    tags[str(k).strip()] = str(v).strip()
    except Exception as exc:
        logger.debug("ffprobe tag read skipped for %s: %s", path.name, exc)
    return tags


def _synchsafe_to_int(b: bytes) -> int:
    return ((b[0] & 0x7F) << 21) | ((b[1] & 0x7F) << 14) | ((b[2] & 0x7F) << 7) | (b[3] & 0x7F)


def _decode_id3_text(payload: bytes) -> str:
    if not payload:
        return ""
    enc = payload[0]
    body = payload[1:]
    try:
        if enc == 0:
            return body.decode("latin-1", errors="replace").rstrip("\x00").strip()
        if enc == 1:
            return body.decode("utf-16", errors="replace").rstrip("\x00").strip()
        if enc == 2:
            return body.decode("utf-16-be", errors="replace").rstrip("\x00").strip()
        if enc == 3:
            return body.decode("utf-8", errors="replace").rstrip("\x00").strip()
        return payload.decode("utf-8", errors="replace").rstrip("\x00").strip()
    except Exception:
        return ""


def _read_raw_tags_binary_fallback(path: Path) -> dict[str, str]:
    """Pure-Python binary fallback for ID3v2, ID3v1, and RIFF INFO tags."""
    tags: dict[str, str] = {}
    try:
        size = path.stat().st_size
        if size < 10:
            return tags
        with path.open("rb") as f:
            head = f.read(min(size, 65536))
            # 1. ID3v2 header
            if head.startswith(b"ID3") and len(head) >= 10:
                version = head[3]
                tag_size = _synchsafe_to_int(head[6:10])
                buf = head[10 : 10 + tag_size] if 10 + tag_size <= len(head) else head[10:]
                pos = 0
                while pos + 10 <= len(buf):
                    frame_id = buf[pos : pos + 4].decode("ascii", errors="ignore")
                    if not frame_id or not frame_id.isalnum():
                        break
                    if version == 4:
                        fsize = _synchsafe_to_int(buf[pos + 4 : pos + 8])
                    else:
                        fsize = struct.unpack(">I", buf[pos + 4 : pos + 8])[0]
                    if fsize <= 0 or pos + 10 + fsize > len(buf):
                        break
                    frame_data = buf[pos + 10 : pos + 10 + fsize]
                    if frame_id.startswith("T") and frame_id != "TXXX":
                        val = _decode_id3_text(frame_data)
                        if val:
                            tags[frame_id] = val
                    pos += 10 + fsize

            # 2. RIFF WAV INFO chunk
            if head.startswith(b"RIFF") and b"INFO" in head:
                info_idx = head.find(b"INFO") + 4
                pos = info_idx
                while pos + 8 <= len(head):
                    cid = head[pos : pos + 4].decode("ascii", errors="ignore")
                    csize = struct.unpack("<I", head[pos + 4 : pos + 8])[0]
                    if not cid.isalnum() or csize <= 0 or pos + 8 + csize > len(head):
                        break
                    val = (
                        head[pos + 8 : pos + 8 + csize]
                        .decode("utf-8", errors="replace")
                        .rstrip("\x00")
                        .strip()
                    )
                    if val:
                        tags[cid] = val
                    pos += 8 + csize + (csize % 2)

            # 3. ID3v1 trailer (last 128 bytes)
            if size >= 128:
                f.seek(size - 128)
                tail = f.read(128)
                if tail.startswith(b"TAG"):
                    title = tail[3:33].decode("latin-1", errors="replace").rstrip("\x00 ").strip()
                    artist = tail[33:63].decode("latin-1", errors="replace").rstrip("\x00 ").strip()
                    album = tail[63:93].decode("latin-1", errors="replace").rstrip("\x00 ").strip()
                    year = tail[93:97].decode("latin-1", errors="replace").rstrip("\x00 ").strip()
                    if title and "title" not in tags:
                        tags["title"] = title
                    if artist and "artist" not in tags:
                        tags["artist"] = artist
                    if album and "album" not in tags:
                        tags["album"] = album
                    if year and "date" not in tags:
                        tags["date"] = year
    except Exception as exc:
        logger.debug("Binary metadata fallback skipped for %s: %s", path.name, exc)
    return tags


def _first_matching(
    lower_map: dict[str, str],
    keys: tuple[str, ...],
    *,
    is_artist: bool = False,
) -> str | None:
    for key in keys:
        if key in lower_map:
            cleaned = _clean_tag_value(lower_map[key], is_artist=is_artist)
            if cleaned:
                return cleaned
    return None


def extract_audio_metadata(path: str | Path | None) -> dict[str, Any]:
    """Inspect an audio file and return normalized, verified metadata fields.

    Returns a dictionary with keys:
      artist, album_artist, title, track_name, album, composer,
      track_number, genre, date, publisher, comment, has_metadata
    Only fields with verified non-empty values are populated.
    Never uses the filename as a fallback.
    """
    empty: dict[str, Any] = {
        "artist": None,
        "album_artist": None,
        "title": None,
        "track_name": None,
        "album": None,
        "composer": None,
        "track_number": None,
        "genre": None,
        "date": None,
        "publisher": None,
        "comment": None,
        "has_metadata": False,
    }
    if not path:
        return empty

    try:
        file_path = Path(path)
        if not file_path.is_file():
            return empty
    except Exception:
        return empty

    raw_tags = _read_raw_tags_av(file_path)
    if not raw_tags:
        raw_tags = _read_raw_tags_ffprobe(file_path)
    if not raw_tags:
        raw_tags = _read_raw_tags_binary_fallback(file_path)
    else:
        # Merge binary fallback for any missing standard fields
        for k, v in _read_raw_tags_binary_fallback(file_path).items():
            raw_tags.setdefault(k, v)

    if not raw_tags:
        return empty

    lower_map: dict[str, str] = {k.lower().strip(): v for k, v in raw_tags.items() if k and v}

    artist = _first_matching(
        lower_map,
        ("artist", "tpe1", "tope", "performer", "©art", "iart", "author", "artist_name"),
        is_artist=True,
    )
    album_artist = _first_matching(
        lower_map,
        ("album_artist", "albumartist", "tpe2", "aart"),
        is_artist=True,
    )
    if not artist and album_artist:
        artist = album_artist

    title = _first_matching(
        lower_map,
        ("title", "tit2", "©nam", "inam", "track_name", "tracktitle"),
    )
    album = _first_matching(
        lower_map,
        ("album", "talb", "©alb", "iprd"),
    )
    composer = _first_matching(
        lower_map,
        ("composer", "tcom", "©wrt", "writer", "lyricist", "text"),
        is_artist=True,
    )
    track_number = _first_matching(
        lower_map,
        ("track", "trck", "trkn", "tracknumber", "track_number"),
    )
    genre = _first_matching(
        lower_map,
        ("genre", "tcon", "©gen", "ignr"),
    )
    date = _first_matching(
        lower_map,
        ("date", "year", "tyer", "tdrc", "©day", "icrd", "originaldate"),
    )
    publisher = _first_matching(
        lower_map,
        ("publisher", "tpub", "label", "record_label", "organization", "copyright", "tcop"),
    )
    comment = _first_matching(
        lower_map,
        ("comment", "comm", "description", "©cmt"),
    )

    has_meta = any(
        val is not None
        for val in (artist, album_artist, title, album, composer, genre, date, publisher)
    )

    return {
        "artist": artist,
        "album_artist": album_artist,
        "title": title,
        "track_name": title,
        "album": album,
        "composer": composer,
        "track_number": track_number,
        "genre": genre,
        "date": date,
        "publisher": publisher,
        "comment": comment,
        "has_metadata": has_meta,
    }
