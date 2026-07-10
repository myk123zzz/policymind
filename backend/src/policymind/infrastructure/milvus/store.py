from collections.abc import Sequence
from datetime import datetime

from policymind.retrieval.ports import HybridCandidates, SearchHit


class MemoryVectorStore:
    """内存向量存储，用于测试。支持租户/权限/时间过滤。"""

    def __init__(self) -> None:
        self._entries: list[dict[str, object]] = []

    async def upsert(
        self,
        chunks: Sequence[object],
        vectors: Sequence[list[float]],
    ) -> None:
        for chunk, vector in zip(chunks, vectors):
            self._entries.append({"chunk": chunk, "vector": vector})

    async def hybrid_search(
        self,
        *,
        query_text: str,
        query_vector: list[float],
        tenant_id: int,
        access_level: int,
        at: datetime,
        limit_per_channel: int,
    ) -> HybridCandidates:
        # 过滤 + 打分
        scored: list[tuple[float, object]] = []
        for entry in self._entries:
            chunk = entry["chunk"]
            if getattr(chunk, "tenant_id", 0) != tenant_id:
                continue
            if getattr(chunk, "access_level", 0) > access_level:
                continue
            eff_from = getattr(chunk, "effective_from", None)
            eff_to = getattr(chunk, "effective_to", None)
            if eff_from is not None and at < eff_from:
                continue
            if eff_to is not None and at > eff_to:
                continue

            vec = entry["vector"]
            sim = self._cosine_sim(query_vector, vec)  # type: ignore[arg-type]
            scored.append((sim, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)

        def to_hits(items: list[tuple[float, object]], channel: str) -> list[SearchHit]:
            return [
                SearchHit(
                    chunk_id=getattr(c, "id", str(i)),
                    score=s,
                    channel=channel,
                    rank=i + 1,
                    text=getattr(c, "text", ""),
                )
                for i, (s, c) in enumerate(items)
            ]

        return HybridCandidates(
            dense=to_hits(scored[:limit_per_channel], "dense"),
            bm25=to_hits(scored[:limit_per_channel], "bm25"),
        )

    async def delete_document_version(
        self, tenant_id: int, version_id: int
    ) -> int:
        before = len(self._entries)
        self._entries = [
            e
            for e in self._entries
            if getattr(e["chunk"], "document_version_id", None) != version_id
        ]
        return before - len(self._entries)

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        dot = 0.0
        for x, y in zip(a, b):
            dot += x * y
        na = 0.0
        for x in a:
            na += x * x
        na = na ** 0.5
        nb = 0.0
        for x in b:
            nb += x * x
        nb = nb ** 0.5
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)  # type: ignore[no-any-return]


class MilvusStore:
    """Milvus 向量存储适配器。"""

    def __init__(self, host: str = "localhost", port: int = 19530) -> None:
        self.host = host
        self.port = port
        self._connected = False

    async def _ensure_connected(self) -> None:
        if not self._connected:
            try:
                from pymilvus import connections  # type: ignore[import-untyped]

                connections.connect(host=self.host, port=str(self.port))
                self._connected = True
            except Exception:
                raise RuntimeError(
                    f"Failed to connect to Milvus at {self.host}:{self.port}"
                )

    async def upsert(
        self, chunks: Sequence[object], vectors: Sequence[list[float]]
    ) -> None:
        await self._ensure_connected()
        # 实际写入 Milvus collection（生产环境需要先创建 collection/schema）
        # 当前阶段标记为已连接，写入逻辑在集成测试时补全

    async def hybrid_search(
        self,
        *,
        query_text: str,
        query_vector: list[float],
        tenant_id: int,
        access_level: int,
        at: datetime,
        limit_per_channel: int,
    ) -> HybridCandidates:
        await self._ensure_connected()
        # 实际 Milvus hybrid search（生产环境需要配置 collection 和 index）
        return HybridCandidates(dense=[], bm25=[])

    async def delete_document_version(
        self, tenant_id: int, version_id: int
    ) -> int:
        await self._ensure_connected()
        return 0
