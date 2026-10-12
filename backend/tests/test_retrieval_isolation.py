"""Ensure vector retrieval is isolated per recording."""

from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np

from app.retrieval.vector_store import FaissVectorStore, VectorMeta


def test_recording_isolation(tmp_path: Path) -> None:
    store = FaissVectorStore(tmp_path)
    rec_a = uuid.uuid4()
    rec_b = uuid.uuid4()

    emb_dim = 8
    emb_a = np.random.randn(2, emb_dim).astype(np.float32)
    emb_b = np.random.randn(2, emb_dim).astype(np.float32)

    meta_a = [
        VectorMeta(0, "موضوع پروژه الف", 0.0, 1.0, ["a1"]),
        VectorMeta(1, "بودجه پروژه الف", 1.0, 2.0, ["a2"]),
    ]
    meta_b = [
        VectorMeta(0, "سلامتی بیمار ب", 0.0, 1.0, ["b1"]),
        VectorMeta(1, "نوبت پزشک ب", 1.0, 2.0, ["b2"]),
    ]

    store.upsert(rec_a, emb_a, meta_a)
    store.upsert(rec_b, emb_b, meta_b)

    query = emb_a[0]
    hits = store.search(rec_a, query, top_k=5)
    assert hits
    for meta, _score in hits:
        assert "بیمار" not in meta.text
        assert meta.segment_ids[0].startswith("a")

    hits_b = store.search(rec_b, emb_b[0], top_k=5)
    assert hits_b
    for meta, _score in hits_b:
        assert "پروژه الف" not in meta.text


def test_delete_index(tmp_path: Path) -> None:
    store = FaissVectorStore(tmp_path)
    rec = uuid.uuid4()
    emb = np.random.randn(1, 4).astype(np.float32)
    store.upsert(rec, emb, [VectorMeta(0, "متن", 0.0, 1.0, ["1"])])
    store.delete(rec)
    assert store.search(rec, emb[0], top_k=1) == []
