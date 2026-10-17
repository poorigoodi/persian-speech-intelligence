"""Multilingual embedding generation with reusable model loading."""

from __future__ import annotations

import threading
from uuid import UUID

import numpy as np

from app.core.config import Settings, get_settings
from app.core.exceptions import ProcessingError
from app.core.logging import get_logger
from app.models.transcript import TranscriptSegment
from app.retrieval.chunking import TranscriptChunk, chunk_segments
from app.retrieval.vector_store import FaissVectorStore, VectorMeta

logger = get_logger(__name__)


class EmbeddingModelManager:
    _lock = threading.Lock()
    _instance: EmbeddingModelManager | None = None

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = None

    @classmethod
    def get_instance(cls, settings: Settings | None = None) -> EmbeddingModelManager:
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
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        from sentence_transformers import SentenceTransformer
                    except ImportError as exc:
                        raise ProcessingError(
                            "sentence-transformers is not installed."
                        ) from exc
                    logger.info(
                        "Loading embedding model '%s' on %s",
                        self.settings.embedding_model,
                        self.settings.embedding_device,
                    )
                    self._model = SentenceTransformer(
                        self.settings.embedding_model,
                        device=self.settings.embedding_device,
                    )
        return self._model


class EmbeddingService:
    def __init__(
        self,
        settings: Settings | None = None,
        model_manager: EmbeddingModelManager | None = None,
        vector_store: FaissVectorStore | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.model_manager = model_manager or EmbeddingModelManager.get_instance(
            self.settings
        )
        self.vector_store = vector_store or FaissVectorStore(self.settings.vector_index_dir)

    def _uses_e5_prefixes(self) -> bool:
        name = self.settings.embedding_model.lower()
        return "e5-" in name or name.endswith("/e5") or "/e5-" in name

    def embed_texts(
        self,
        texts: list[str],
        *,
        prefix: str | None = None,
    ) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        model = self.model_manager.get_model()
        if prefix:
            texts = [f"{prefix}{t}" for t in texts]
        vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return np.asarray(vectors, dtype=np.float32)

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        prefix = "passage: " if self._uses_e5_prefixes() else None
        return self.embed_texts(texts, prefix=prefix)

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        prefix = "query: " if self._uses_e5_prefixes() else None
        return self.embed_texts(texts, prefix=prefix)

    def index_recording(
        self,
        recording_id: UUID,
        segments: list[TranscriptSegment],
    ) -> list[TranscriptChunk]:
        chunks = chunk_segments(
            recording_id,
            segments,
            chunk_size_chars=self.settings.chunk_size_chars,
            chunk_overlap_chars=self.settings.chunk_overlap_chars,
        )
        if not chunks:
            self.vector_store.delete(recording_id)
            return []

        embeddings = self.embed_passages([c.text for c in chunks])
        metadatas = [
            VectorMeta(
                chunk_index=c.chunk_index,
                text=c.text,
                start_time=c.start_time,
                end_time=c.end_time,
                segment_ids=c.segment_ids,
            )
            for c in chunks
        ]
        self.vector_store.upsert(recording_id, embeddings, metadatas)
        return chunks

    def delete_recording_index(self, recording_id: UUID) -> None:
        self.vector_store.delete(recording_id)
