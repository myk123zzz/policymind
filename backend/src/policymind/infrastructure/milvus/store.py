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
    """Milvus 向量存储适配器，基于 pymilvus。

    Schema 包含 Task 5 要求的全部检索与安全字段：
    id, tenant_id, document_id, document_version_id, access_level,
    effective_from, effective_to, text, dense_vector.
    """

    def __init__(self, host: str = "localhost", port: int = 19530) -> None:
        self.host = host
        self.port = port
        self._ready = False

    @staticmethod
    def _make_schema() -> object:
        from pymilvus import (  # type: ignore[import-untyped]
            CollectionSchema,
            DataType,
            FieldSchema,
        )

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="tenant_id", dtype=DataType.INT64),
            FieldSchema(name="document_id", dtype=DataType.INT64),
            FieldSchema(name="document_version_id", dtype=DataType.INT64),
            FieldSchema(name="access_level", dtype=DataType.INT64),
            FieldSchema(name="effective_from", dtype=DataType.INT64),
            FieldSchema(name="effective_to", dtype=DataType.INT64),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=DIM),
        ]
        return CollectionSchema(fields)

    async def _ensure_ready(self) -> None:
        if self._ready:
            return
        try:
            from pymilvus import (
                Collection,
                connections,
                utility,
            )

            alias = f"pm_{hashlib.md5(f'{self.host}:{self.port}'.encode()).hexdigest()[:8]}"
            connections.connect(alias=alias, host=self.host, port=str(self.port))

            if not utility.has_collection(COLLECTION_NAME, using=alias):
                schema = self._make_schema()
                Collection(name=COLLECTION_NAME, schema=schema, using=alias)
            else:
                Collection(name=COLLECTION_NAME, using=alias)

            self._alias: str = alias
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
        data: list[list[object]] = [[], [], [], [], [], [], [], [], []]
        for chunk, vec in zip(chunks, vectors):
            eff_from = getattr(chunk, "effective_from", None)
            eff_to = getattr(chunk, "effective_to", None)
            data[0].append(getattr(chunk, "id", hashlib.md5(str(chunk).encode()).hexdigest()[:16]))
            data[1].append(getattr(chunk, "tenant_id", 0))
            data[2].append(getattr(chunk, "document_id", 0))
            data[3].append(getattr(chunk, "document_version_id", 0))
            data[4].append(getattr(chunk, "access_level", 1))
            data[5].append(int(eff_from.timestamp()) if eff_from else 0)
            data[6].append(int(eff_to.timestamp()) if eff_to else 0)
            data[7].append(getattr(chunk, "text", ""))
            data[8].append(vec)
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

        at_ts = int(at.timestamp())
        filter_expr = (
            f"tenant_id == {tenant_id}"
            f" && access_level <= {access_level}"
            f" && effective_from <= {at_ts}"
            f" && (effective_to == 0 || effective_to > {at_ts})"
        )
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        results = col.search(
            data=[query_vector],
            anns_field="dense_vector",
            param=search_params,
            limit=limit_per_channel,
            expr=filter_expr,
            output_fields=["id", "tenant_id", "text", "document_version_id"],
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
        expr = f"tenant_id == {tenant_id} && document_version_id == {version_id}"
        try:
            result = col.query(expr=expr, output_fields=["id"], limit=10000)
            ids = [r["id"] for r in result]
            if ids:
                col.delete(f"id in {ids}")
            return len(ids)
        except Exception:
            return 0
