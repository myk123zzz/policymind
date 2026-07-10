import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from policymind.retrieval.citations import Citation, build_citations
from policymind.retrieval.fusion import rrf_fuse
from policymind.retrieval.parent_expansion import expand_parents
from policymind.retrieval.ports import (
    EmbeddingProvider,
    HybridCandidates,
    Reranker,
    SearchHit,
    VectorStore,
)
from policymind.retrieval.rerank import NoopReranker

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievalBundle:
    query: str
    hits: list[SearchHit]
    citations: list[Citation]
    context: str
    degraded: bool = False


class RetrievalService:
    def __init__(
        self,
        vector_store: VectorStore,
        embedder: EmbeddingProvider,
        reranker: Reranker | None = None,
    ) -> None:
        self._store = vector_store
        self._embedder = embedder
        self._reranker: Reranker = reranker or NoopReranker()

    async def retrieve(
        self,
        *,
        tenant_id: int,
        access_level: int,
        query: str,
        at: datetime | None = None,
        top_k: int = 8,
    ) -> RetrievalBundle:
        if at is None:
            at = datetime.now(UTC)

        query_vector = await self._embedder.embed_query(query)
        candidates: HybridCandidates = await self._store.hybrid_search(
            query_text=query,
            query_vector=query_vector,
            tenant_id=tenant_id,
            access_level=access_level,
            at=at,
            limit_per_channel=30,
        )

        # RRF 融合
        fused = rrf_fuse(
            {"dense": candidates.dense, "bm25": candidates.bm25},
            limit=30,
        )

        # Rerank（降级标记）
        degraded = False
        try:
            reranked = await self._reranker.rerank(
                query=query, candidates=fused, limit=top_k
            )
        except Exception:
            logger.warning("Rerank failed, falling back to RRF order")
            reranked = fused[:top_k]
            degraded = True

        # Parent Expansion
        expanded = expand_parents(reranked)

        # Citation
        citations = build_citations(expanded)

        return RetrievalBundle(
            query=query,
            hits=expanded,
            citations=citations,
            context="\n\n".join(h.text for h in expanded),
            degraded=degraded,
        )
