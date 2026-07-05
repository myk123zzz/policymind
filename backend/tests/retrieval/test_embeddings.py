import pytest


async def test_memory_embedding_returns_correct_dimension() -> None:
    """内存 Embedding 返回指定维度的向量。"""
    from policymind.retrieval.embeddings import MemoryEmbeddingProvider

    provider = MemoryEmbeddingProvider(dimension=128)
    result = await provider.embed_query("test query")
    assert len(result) == 128


async def test_memory_embedding_batch_returns_correct_count() -> None:
    """批量 Embedding 返回正确数量的向量。"""
    from policymind.retrieval.embeddings import MemoryEmbeddingProvider

    provider = MemoryEmbeddingProvider(dimension=64)
    results = await provider.embed_documents(["doc1", "doc2", "doc3"])
    assert len(results) == 3
    for vec in results:
        assert len(vec) == 64


async def test_embedding_failure_raises() -> None:
    """Embedding 失败抛出 EmbeddingUnavailable。"""
    from policymind.core.errors import EmbeddingUnavailable

    class FailingProvider:
        dimension = 128
        model_name = "fail"

        async def embed_documents(self, texts):
            raise EmbeddingUnavailable("Service down")

        async def embed_query(self, text):
            raise EmbeddingUnavailable("Service down")

    provider = FailingProvider()
    with pytest.raises(EmbeddingUnavailable):
        await provider.embed_query("test")  # type: ignore[union-attr]

    with pytest.raises(EmbeddingUnavailable):
        await provider.embed_documents(["test"])  # type: ignore[union-attr]
