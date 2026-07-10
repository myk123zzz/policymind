from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(slots=True)
class SearchHit:
    chunk_id: str
    score: float
    channel: str
    rank: int
    text: str = ""


@dataclass(slots=True)
class HybridCandidates:
    dense: list[SearchHit]
    bm25: list[SearchHit]


class EmbeddingProvider(Protocol):
    dimension: int
    model_name: str

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...
    async def embed_query(self, text: str) -> list[float]: ...


class VectorStore(Protocol):
    async def upsert(
        self,
        chunks: Sequence[object],
        vectors: Sequence[list[float]],
    ) -> None: ...

    async def hybrid_search(
        self,
        *,
        query_text: str,
        query_vector: list[float],
        tenant_id: int,
        access_level: int,
        at: datetime,
        limit_per_channel: int,
    ) -> HybridCandidates: ...

    async def delete_document_version(
        self, tenant_id: int, version_id: int
    ) -> int: ...


class Reranker(Protocol):
    async def rerank(
        self,
        query: str,
        candidates: Sequence[SearchHit],
        limit: int,
    ) -> list[SearchHit]: ...
