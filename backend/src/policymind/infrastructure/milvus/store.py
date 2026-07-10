import hashlib
from collections.abc import Sequence
from datetime import datetime

from policymind.retrieval.ports import HybridCandidates, SearchHit

COLLECTION_NAME = "policy_chunks"
DIM = 128


class MemoryVectorStore:
    """内存向量存储，用于测试。支持租户/权限/时间过滤和双通道检索。"""

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
        # 过滤
        candidates: list[tuple[object, list[float]]] = []
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
            candidates.append((chunk, entry["vector"]))  # type: ignore[arg-type]

        # Dense: 余弦相似度
        dense_scored = [(self._cosine_sim(query_vector, vec), c) for c, vec in candidates]
        dense_scored.sort(key=lambda x: x[0], reverse=True)

        # BM25: 基于 query_text 的关键词匹配分数
        query_terms = set(query_text.lower().split())
        bm25_scored: list[tuple[float, object]] = []
        for c, _ in candidates:
            text = getattr(c, "text", "").lower()
            score = sum(1.0 for t in query_terms if t in text)
            if score > 0:
                bm25_scored.append((score, c))
        bm25_scored.sort(key=lambda x: x[0], reverse=True)

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
            dense=to_hits(dense_scored[:limit_per_channel], "dense"),
            bm25=to_hits(bm25_scored[:limit_per_channel], "bm25"),
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
    """Milvus 向量存储，支持 Dense ANN + BM25 双通道 Hybrid Search。"""

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
            Function,
            FunctionType,
        )

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="tenant_id", dtype=DataType.INT64),
            FieldSchema(name="document_id", dtype=DataType.INT64),
            FieldSchema(name="document_version_id", dtype=DataType.INT64),
            FieldSchema(name="access_level", dtype=DataType.INT64),
            FieldSchema(name="effective_from", dtype=DataType.INT64),
            FieldSchema(name="effective_to", dtype=DataType.INT64),
            FieldSchema(
                name="text", dtype=DataType.VARCHAR,
                max_length=65535, enable_analyzer=True,
            ),
            FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=DIM),
            FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
        ]

        # BM25 Function: text → sparse_vector
        bm25_fn = Function(
            name="bm25",
            function_type=FunctionType.BM25,
            input_field_names=["text"],
            output_field_names=["sparse_vector"],
        )

        return CollectionSchema(fields, functions=[bm25_fn])

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
                col = Collection(name=COLLECTION_NAME, schema=schema, using=alias)
                # 为 dense 创建索引
                col.create_index(
                    field_name="dense_vector",
                    index_params={
                        "metric_type": "COSINE",
                        "index_type": "IVF_FLAT",
                        "params": {"nlist": 128},
                    },
                )
                # 为 sparse 创建索引
                col.create_index(
                    field_name="sparse_vector",
                    index_params={"metric_type": "BM25", "index_type": "SPARSE_INVERTED_INDEX"},
                )

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
        data: list[list[object]] = [[], [], [], [], [], [], [], [], [], []]
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
            data[9].append({})  # sparse_vector 由 BM25 Function 自动生成
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
        from pymilvus import (
            Collection,
        )

        col = Collection(name=COLLECTION_NAME, using=self._alias)
        col.load()

        at_ts = int(at.timestamp())
        filter_expr = (
            f"tenant_id == {tenant_id}"
            f" && access_level <= {access_level}"
            f" && effective_from <= {at_ts}"
            f" && (effective_to == 0 || effective_to > {at_ts})"
        )

        # 独立 dense 搜索
        dense_param = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        dense_results = col.search(
            data=[query_vector],
            anns_field="dense_vector",
            param=dense_param,
            limit=limit_per_channel,
            expr=filter_expr,
            output_fields=["id", "text"],
        )

        # 独立 sparse/BM25 搜索
        from pymilvus import SparseSearchRequest
        sparse_results = col.search(
            data=[SparseSearchRequest(query_text=query_text)],
            anns_field="sparse_vector",
            param={"metric_type": "BM25"},
            limit=limit_per_channel,
            expr=filter_expr,
            output_fields=["id", "text"],
        )

        def _build_hits(results: object, channel: str) -> list[SearchHit]:
            hits: list[SearchHit] = []
            for i, match in enumerate(results[0]):  # type: ignore[index]
                hits.append(
                    SearchHit(
                        chunk_id=str(match.entity.get("id", "")),
                        score=float(match.distance),
                        channel=channel,
                        rank=i + 1,
                        text=str(match.entity.get("text", "")),
                    )
                )
            return hits

        return HybridCandidates(
            dense=_build_hits(dense_results, "dense"),
            bm25=_build_hits(sparse_results, "bm25"),
        )

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
