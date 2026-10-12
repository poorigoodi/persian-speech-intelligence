"""Recording-isolated transcript retriever."""

from __future__ import annotations

from uuid import UUID

from app.core.config import Settings, get_settings
from app.retrieval.vector_store import FaissVectorStore, VectorMeta
from app.services.embedding_service import EmbeddingService


class TranscriptRetriever:
    """Retrieve relevant chunks only from the specified recording."""

    def __init__(
        self,
        settings: Settings | None = None,
        embedding_service: EmbeddingService | None = None,
        vector_store: FaissVectorStore | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embedding_service = embedding_service or EmbeddingService(self.settings)
        self.vector_store = vector_store or self.embedding_service.vector_store

    def retrieve(
        self,
        recording_id: UUID,
        question: str,
        *,
        top_k: int | None = None,
    ) -> list[tuple[VectorMeta, float]]:
        """Search only within the given recording's vector index."""
        k = top_k or self.settings.retrieval_top_k
        query_vec = self.embedding_service.embed_texts([question])
        if query_vec.size == 0:
            return []
        return self.vector_store.search(recording_id, query_vec[0], top_k=k)
