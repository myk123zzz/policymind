from dataclasses import dataclass
from datetime import UTC, datetime

import pytest


@dataclass
class TestChunk:
    id: str
    text: str
    tenant_id: int = 1
    access_level: int = 1
    effective_from: datetime | None = None
    effective_to: datetime | None = None


@pytest.fixture
def store():
    from policymind.infrastructure.milvus.store import MemoryVectorStore

    return MemoryVectorStore()


@pytest.fixture
def embedder():
    from policymind.retrieval.embeddings import MemoryEmbeddingProvider

    return MemoryEmbeddingProvider(dimension=128)


async def test_retrieval_service_main_chain(store, embedder) -> None:
    """RetrievalService 主链：embed → search → RRF → citation。"""
    from policymind.retrieval.service import RetrievalService

    now = datetime.now(UTC)
    chunks = [
        TestChunk(id="c1", text="Policy on procurement approval."),
        TestChunk(id="c2", text="Travel reimbursement guidelines."),
    ]
    vectors = [await embedder.embed_query(c.text) for c in chunks]
    await store.upsert(chunks=chunks, vectors=vectors)

    svc = RetrievalService(vector_store=store, embedder=embedder)
    result = await svc.retrieve(
        tenant_id=1, access_level=5, query="procurement approval", at=now
    )

    assert len(result.hits) > 0
    assert len(result.citations) > 0
    assert "procurement" in result.context.lower()
    assert not result.degraded


async def test_retrieval_service_rerank_degraded(store, embedder) -> None:
    """Rerank 失败时降级。"""
    from policymind.retrieval.service import RetrievalService

    now = datetime.now(UTC)
    chunks = [TestChunk(id="c1", text="Some content here.")]
    vectors = [await embedder.embed_query(c.text) for c in chunks]
    await store.upsert(chunks=chunks, vectors=vectors)

    class FailingReranker:
        async def rerank(self, query, candidates, limit):
            raise RuntimeError("rerank down")

    svc = RetrievalService(
        vector_store=store, embedder=embedder, reranker=FailingReranker()
    )
    result = await svc.retrieve(
        tenant_id=1, access_level=5, query="content", at=now, top_k=1
    )

    assert result.degraded
    assert len(result.hits) == 1
