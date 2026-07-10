import hashlib
from collections.abc import Sequence
from datetime import datetime

from policymind.retrieval.ports import HybridCandidates, SearchHit

COLLECTION_NAME = "policy_chunks"
DIM = 128


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
    """Milvus 向量存储适配器，基于 pymilvus。"""

    def __init__(self, host: str = "localhost", port: int = 19530) -> None:
        self.host = host
        self.port = port
        self._ready = False

    async def _ensure_ready(self) -> None:
        if self._ready:
            return
        try:
            from pymilvus import (  # type: ignore[import-untyped]
                Collection,
                CollectionSchema,
                DataType,
                FieldSchema,
                connections,
                utility,
            )

            alias = f"pm_{hashlib.md5(f'{self.host}:{self.port}'.encode()).hexdigest()[:8]}"
            connections.connect(alias=alias, host=self.host, port=str(self.port))

            if not utility.has_collection(COLLECTION_NAME, using=alias):
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
                    FieldSchema(name="tenant_id", dtype=DataType.INT64),
                    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=DIM),
                ]
                schema = CollectionSchema(fields)
                Collection(name=COLLECTION_NAME, schema=schema, using=alias)
            else:
                Collection(name=COLLECTION_NAME, using=alias)

            self._alias = alias
            self._ready = True
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Milvus at {self.host}:{self.port}: {e}"
            ) from e

    async def upsert(
        self, chunks: Sequence[object], vectors: Sequence[list[float]]
    ) -> None:
        await self._ensure_ready()
        from pymilvus import Collection

        col = Collection(name=COLLECTION_NAME, using=self._alias)
        data: list[list[object]] = [[], [], [], []]
        for chunk, vec in zip(chunks, vectors):
            data[0].append(getattr(chunk, "id", hashlib.md5(str(chunk).encode()).hexdigest()[:16]))
            data[1].append(getattr(chunk, "tenant_id", 0))
            data[2].append(getattr(chunk, "text", ""))
            data[3].append(vec)
        col.insert(data)

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
        await self._ensure_ready()
        from pymilvus import Collection

        col = Collection(name=COLLECTION_NAME, using=self._alias)
        col.load()

        filter_expr = f"tenant_id == {tenant_id}"
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        results = col.search(
            data=[query_vector],
            anns_field="dense_vector",
            param=search_params,
            limit=limit_per_channel,
            expr=filter_expr,
            output_fields=["id", "tenant_id", "text"],
        )

        hits: list[SearchHit] = []
        for i, match in enumerate(results[0]):
            hits.append(
                SearchHit(
                    chunk_id=str(match.entity.get("id", "")),
                    score=float(match.distance),
                    channel="dense",
                    rank=i + 1,
                    text=str(match.entity.get("text", "")),
                )
            )

        return HybridCandidates(dense=hits, bm25=hits)

    async def delete_document_version(
        self, tenant_id: int, version_id: int
    ) -> int:
        await self._ensure_ready()
        from pymilvus import Collection

        col = Collection(name=COLLECTION_NAME, using=self._alias)
        expr = f"tenant_id == {tenant_id}"
        result = col.query(expr=expr, output_fields=["id"], limit=1000)
        ids = [r["id"] for r in result]
        if ids:
            col.delete(f"id in {ids}")
        return len(ids)
