"""FAISS-backed per-recording vector index with persisted metadata."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import UUID

import numpy as np

from app.core.exceptions import ProcessingError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VectorMeta:
    chunk_index: int
    text: str
    start_time: float
    end_time: float
    segment_ids: list[str]


class FaissVectorStore:
    """Persist one FAISS index + metadata JSON per recording for isolation."""

    def __init__(self, index_dir: Path) -> None:
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _paths(self, recording_id: UUID) -> tuple[Path, Path]:
        base = self.index_dir / str(recording_id)
        return base.with_suffix(".faiss"), base.with_suffix(".meta.json")

    def delete(self, recording_id: UUID) -> None:
        index_path, meta_path = self._paths(recording_id)
        index_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)

    def upsert(
        self,
        recording_id: UUID,
        embeddings: np.ndarray,
        metadatas: list[VectorMeta],
    ) -> None:
        if embeddings.size == 0 or not metadatas:
            self.delete(recording_id)
            return
        if embeddings.ndim != 2:
            raise ProcessingError("Embeddings must be a 2D array.")
        if len(metadatas) != embeddings.shape[0]:
            raise ProcessingError("Metadata count must match embedding count.")

        try:
            import faiss
        except ImportError as exc:
            raise ProcessingError("faiss-cpu is not installed.") from exc

        vectors = embeddings.astype(np.float32)
        # L2-normalize for cosine similarity via inner product
        faiss.normalize_L2(vectors)
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)

        index_path, meta_path = self._paths(recording_id)
        with self._lock:
            faiss.write_index(index, str(index_path))
            meta_path.write_text(
                json.dumps([asdict(m) for m in metadatas], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def search(
        self,
        recording_id: UUID,
        query_embedding: np.ndarray,
        *,
        top_k: int = 5,
    ) -> list[tuple[VectorMeta, float]]:
        index_path, meta_path = self._paths(recording_id)
        if not index_path.exists() or not meta_path.exists():
            return []

        try:
            import faiss
        except ImportError as exc:
            raise ProcessingError("faiss-cpu is not installed.") from exc

        with self._lock:
            index = faiss.read_index(str(index_path))
            metadatas = [
                VectorMeta(**item)
                for item in json.loads(meta_path.read_text(encoding="utf-8"))
            ]

        if index.ntotal == 0:
            return []

        query = query_embedding.astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(query)
        k = min(top_k, index.ntotal)
        scores, indices = index.search(query, k)

        results: list[tuple[VectorMeta, float]] = []
        for score, idx in zip(scores[0], indices[0], strict=True):
            if idx < 0 or idx >= len(metadatas):
                continue
            results.append((metadatas[idx], float(score)))
        return results
