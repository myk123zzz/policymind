from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest


@dataclass
class FakeChunk:
    id: str
    text: str
    tenant_id: int = 1
    access_level: int = 1
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    document_version_id: int = 1


@pytest.fixture
def now():
    return datetime(2025, 6, 15, tzinfo=UTC)


@pytest.fixture
def store():
    from policymind.infrastructure.milvus.store import MemoryVectorStore

    return MemoryVectorStore()


@pytest.fixture
def vector():
    return [0.1] * 128


async def test_filters_by_tenant(store, vector, now) -> None:
    c1 = FakeChunk(id="c1", text="t1", tenant_id=1)
    c2 = FakeChunk(id="c2", text="t2", tenant_id=2)
    await store.upsert(chunks=[c1, c2], vectors=[vector, vector])

    result = await store.hybrid_search(
        query_text="test", query_vector=vector,
        tenant_id=1, access_level=5, at=now, limit_per_channel=10,
    )
    ids = {h.chunk_id for h in result.dense}
    assert "c1" in ids
    assert "c2" not in ids


async def test_filters_by_access_level(store, vector, now) -> None:
    c1 = FakeChunk(id="c1", text="low", access_level=1)
    c2 = FakeChunk(id="c2", text="high", access_level=5)
    await store.upsert(chunks=[c1, c2], vectors=[vector, vector])

    result = await store.hybrid_search(
        query_text="test", query_vector=vector,
        tenant_id=1, access_level=2, at=now, limit_per_channel=10,
    )
    ids = {h.chunk_id for h in result.dense}
    assert "c1" in ids
    assert "c2" not in ids


async def test_filters_by_time(store, vector, now) -> None:
    past = FakeChunk(
        id="past", text="old",
        effective_from=now - timedelta(days=30),
        effective_to=now - timedelta(days=10),
    )
    current = FakeChunk(
        id="current", text="now",
        effective_from=now - timedelta(days=5),
    )
    await store.upsert(chunks=[past, current], vectors=[vector, vector])

    result = await store.hybrid_search(
        query_text="test", query_vector=vector,
        tenant_id=1, access_level=5, at=now, limit_per_channel=10,
    )
    ids = {h.chunk_id for h in result.dense}
    assert "current" in ids
    assert "past" not in ids


async def test_delete_by_version(store, vector, now) -> None:
    c1 = FakeChunk(id="c1", text="keep", document_version_id=1)
    c2 = FakeChunk(id="c2", text="drop", document_version_id=2)
    await store.upsert(chunks=[c1, c2], vectors=[vector, vector])

    await store.delete_document_version(tenant_id=1, version_id=2)

    result = await store.hybrid_search(
        query_text="test", query_vector=vector,
        tenant_id=1, access_level=5, at=now, limit_per_channel=10,
    )
    ids = {h.chunk_id for h in result.dense}
    assert "c1" in ids
    assert "c2" not in ids
