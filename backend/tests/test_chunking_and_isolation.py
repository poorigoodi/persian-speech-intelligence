"""Chunking and retrieval isolation tests."""

from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np

from app.models.transcript import TranscriptSegment
from app.retrieval.chunking import chunk_segments
from app.retrieval.vector_store import FaissVectorStore, VectorMeta


def _seg(recording_id, idx: int, text: str) -> TranscriptSegment:
    return TranscriptSegment(
        id=uuid.uuid4(),
        recording_id=recording_id,
        segment_index=idx,
        start_time=float(idx),
        end_time=float(idx) + 1.0,
        original_text=text,
        normalized_text=text,
    )


def test_chunk_segments_preserves_recording_id() -> None:
    rid = uuid.uuid4()
    segments = [_seg(rid, i, f"متن شماره {i} " + ("کلمه " * 20)) for i in range(5)]
    chunks = chunk_segments(rid, segments, chunk_size_chars=80, chunk_overlap_chars=10)
    assert chunks
    assert all(c.recording_id == rid for c in chunks)
    assert all(c.segment_ids for c in chunks)


def test_vector_store_recording_isolation(tmp_path: Path) -> None:
    store = FaissVectorStore(tmp_path)
    a = uuid.uuid4()
    b = uuid.uuid4()

    emb_a = np.array([[1.0, 0.0], [0.9, 0.1]], dtype=np.float32)
    emb_b = np.array([[0.0, 1.0]], dtype=np.float32)

    store.upsert(
        a,
        emb_a,
        [
            VectorMeta(0, "secret A1", 0.0, 1.0, ["s1"]),
            VectorMeta(1, "secret A2", 1.0, 2.0, ["s2"]),
        ],
    )
    store.upsert(
        b,
        emb_b,
        [VectorMeta(0, "public B", 0.0, 1.0, ["s3"])],
    )

    # Query similar to A should not return B content when searching A
    hits_a = store.search(a, np.array([1.0, 0.0], dtype=np.float32), top_k=5)
    assert hits_a
    assert all("secret A" in meta.text for meta, _ in hits_a)

    hits_b = store.search(b, np.array([0.0, 1.0], dtype=np.float32), top_k=5)
    assert hits_b
    assert all(meta.text == "public B" for meta, _ in hits_b)
