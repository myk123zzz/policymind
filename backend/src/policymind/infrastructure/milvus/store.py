from collections.abc import Sequence

from policymind.retrieval.ports import HybridCandidates, SearchHit


class MemoryVectorStore:
    """内存向量存储，用于测试。"""

    def __init__(self) -> None:
        self._chunks: list[dict[str, object]] = []
        self._vectors: list[list[float]] = []

    async def upsert(
        self,
        chunks: Sequence[object],
        vectors: Sequence[list[float]],
    ) -> None:
        for chunk, vector in zip(chunks, vectors):
            self._chunks.append({"chunk": chunk, "vector": vector})
            self._vectors.append(vector)

    async def hybrid_search(
        self,
        *,
        query_text: str,
        query_vector: list[float],
        tenant_id: int,
        access_level: int,
        limit_per_channel: int,
    ) -> HybridCandidates:
        # 简单余弦相似度搜索
        scored: list[tuple[float, object]] = []
        for entry in self._chunks:
            vec = entry["vector"]
            sim = self._cosine_sim(query_vector, vec)  # type: ignore[arg-type]
            scored.append((sim, entry["chunk"]))

        scored.sort(key=lambda x: x[0], reverse=True)

        dense_hits = [
            SearchHit(
                chunk_id=getattr(c, "id", str(i)),
                score=s,
                channel="dense",
                rank=i + 1,
                text=getattr(c, "text", ""),
            )
            for i, (s, c) in enumerate(scored[:limit_per_channel])
        ]

        # BM25 在这里简单返回分数最高的文本匹配
        bm25_hits = [
            SearchHit(
                chunk_id=getattr(c, "id", str(i)),
                score=s,
                channel="bm25",
                rank=i + 1,
                text=getattr(c, "text", ""),
            )
            for i, (s, c) in enumerate(scored[:limit_per_channel])
        ]

        return HybridCandidates(dense=dense_hits, bm25=bm25_hits)

    async def delete_document_version(
        self, tenant_id: int, version_id: int
    ) -> int:
        before = len(self._chunks)
        self._chunks = [
            e
            for e in self._chunks
            if getattr(e["chunk"], "document_version_id", None) != version_id
        ]
        return before - len(self._chunks)

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        dot = 0.0
        for x, y in zip(a, b):
            dot += x * y
        norm_a = 0.0
        for x in a:
            norm_a += x * x
        norm_a = norm_a ** 0.5
        norm_b = 0.0
        for x in b:
            norm_b += x * x
        norm_b = norm_b ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)  # type: ignore[no-any-return]


class MilvusStore:
    """Milvus 向量存储适配器（Task 5+ 完整实现）。"""

    def __init__(
        self, host: str = "localhost", port: int = 19530
    ) -> None:
        self.host = host
        self.port = port

    async def upsert(
        self, chunks: Sequence[object], vectors: Sequence[list[float]]
    ) -> None:
        raise NotImplementedError("Milvus integration pending Task 5+")

    async def hybrid_search(self, **kwargs: object) -> HybridCandidates:
        raise NotImplementedError("Milvus integration pending Task 5+")

    async def delete_document_version(
        self, tenant_id: int, version_id: int
    ) -> int:
        raise NotImplementedError("Milvus integration pending Task 5+")
