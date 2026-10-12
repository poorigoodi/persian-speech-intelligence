"""Transcript chunking that preserves timestamp metadata."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.models.transcript import TranscriptSegment


@dataclass
class TranscriptChunk:
    recording_id: UUID
    chunk_index: int
    text: str
    start_time: float
    end_time: float
    segment_ids: list[str]


def chunk_segments(
    recording_id: UUID,
    segments: list[TranscriptSegment],
    *,
    chunk_size_chars: int = 500,
    chunk_overlap_chars: int = 80,
) -> list[TranscriptChunk]:
    """Merge consecutive transcript segments into overlapping text chunks."""
    if not segments:
        return []

    chunks: list[TranscriptChunk] = []
    buffer_texts: list[str] = []
    buffer_ids: list[str] = []
    buffer_start: float | None = None
    buffer_end: float = 0.0
    buffer_len = 0
    chunk_index = 0

    def flush() -> None:
        nonlocal buffer_texts, buffer_ids, buffer_start, buffer_end, buffer_len, chunk_index
        if not buffer_texts or buffer_start is None:
            return
        chunks.append(
            TranscriptChunk(
                recording_id=recording_id,
                chunk_index=chunk_index,
                text=" ".join(buffer_texts).strip(),
                start_time=buffer_start,
                end_time=buffer_end,
                segment_ids=list(buffer_ids),
            )
        )
        chunk_index += 1

        # Overlap: keep trailing text approximately chunk_overlap_chars
        if chunk_overlap_chars <= 0 or not buffer_texts:
            buffer_texts, buffer_ids = [], []
            buffer_start = None
            buffer_len = 0
            return

        overlap_texts: list[str] = []
        overlap_ids: list[str] = []
        overlap_len = 0
        for text, seg_id in zip(
            reversed(buffer_texts), reversed(buffer_ids), strict=True
        ):
            overlap_texts.insert(0, text)
            overlap_ids.insert(0, seg_id)
            overlap_len += len(text) + 1
            if overlap_len >= chunk_overlap_chars:
                break
        buffer_texts = overlap_texts
        buffer_ids = overlap_ids
        buffer_len = overlap_len
        buffer_start = buffer_end  # approximate; refined as new segs arrive

    for seg in segments:
        text = (seg.normalized_text or seg.original_text or "").strip()
        if not text:
            continue
        seg_id = str(seg.id)
        if buffer_start is None:
            buffer_start = float(seg.start_time)

        if buffer_len + len(text) > chunk_size_chars and buffer_texts:
            flush()
            if buffer_start is None:
                buffer_start = float(seg.start_time)

        buffer_texts.append(text)
        buffer_ids.append(seg_id)
        buffer_end = float(seg.end_time)
        buffer_len += len(text) + 1

    flush()
    return chunks
