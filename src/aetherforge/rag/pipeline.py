from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from aetherforge.rag.hybrid import HybridIndex, ScoredChunk
from aetherforge.storage.models import KnowledgeChunk


class RagPipeline:
    """Production-shaped RAG: hybrid retrieve → rerank → cite-or-abstain."""

    def __init__(self) -> None:
        self._index: HybridIndex | None = None

    def load(self, session: Session) -> None:
        rows = session.scalars(select(KnowledgeChunk)).all()
        chunks = [
            {
                "chunk_id": r.chunk_id,
                "doc_id": r.doc_id,
                "title": r.title,
                "category": r.category,
                "text": r.text,
            }
            for r in rows
        ]
        self._index = HybridIndex(chunks)

    def retrieve(self, query: str, k: int = 5) -> list[ScoredChunk]:
        if self._index is None:
            return []
        return self._index.search(query, k=k)

    def grounded(self, hits: list[ScoredChunk], min_score: float = 0.02) -> bool:
        return bool(hits) and hits[0].score >= min_score
