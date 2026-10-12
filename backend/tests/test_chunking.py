"""Transcript chunking tests."""

from __future__ import annotations

import uuid

from app.models.transcript import TranscriptSegment
from app.retrieval.chunking import chunk_segments


def test_chunk_segments_preserves_timestamps() -> None:
    recording_id = uuid.uuid4()
    segments = []
    for i in range(5):
        segments.append(
            TranscriptSegment(
                id=uuid.uuid4(),
                recording_id=recording_id,
                segment_index=i,
                start_time=float(i),
                end_time=float(i) + 0.9,
                original_text=f"جمله شماره {i} " + ("متن " * 20),
                normalized_text=f"جمله شماره {i} " + ("متن " * 20),
            )
        )

    chunks = chunk_segments(
        recording_id,
        segments,
        chunk_size_chars=120,
        chunk_overlap_chars=20,
    )
    assert chunks
    assert chunks[0].start_time == 0.0
    assert chunks[-1].end_time >= chunks[0].start_time
    assert all(c.recording_id == recording_id for c in chunks)
