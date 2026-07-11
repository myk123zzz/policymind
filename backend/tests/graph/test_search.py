import pytest_asyncio

from policymind.graph.path_ranker import rank_paths
from policymind.graph.repository import GraphPath


@pytest_asyncio.fixture
async def repo():
    from policymind.graph.repository import MemoryGraphRepository

    return MemoryGraphRepository()


def test_path_ranker_prefers_higher_confidence() -> None:
    p1 = GraphPath(
        entities=[
            {"id": "a", "type": "Policy", "name": "A", "confidence": 0.9},
        ],
        relations=[],
    )
    p2 = GraphPath(
        entities=[
            {"id": "b", "type": "Policy", "name": "B", "confidence": 0.5},
        ],
        relations=[],
    )
    ranked = rank_paths([p1, p2])
    assert ranked[0].entities[0]["id"] == "a"


def test_path_ranker_penalizes_longer_paths() -> None:
    p1 = GraphPath(
        entities=[{"id": "a", "type": "Policy", "name": "A", "confidence": 0.9}],
        relations=[],
    )
    p2 = GraphPath(
        entities=[{"id": "b", "type": "Policy", "name": "B", "confidence": 0.9}],
        relations=[
            {"type": "APPLIES_TO", "confidence": 0.9},
            {"type": "OWNED_BY", "confidence": 0.9},
        ],
    )
    ranked = rank_paths([p1, p2])
    # Shorter path should rank higher when confidences are equal
    assert ranked[0].entities[0]["id"] == "a"


async def test_search_service_builds_context(repo) -> None:
    from policymind.graph.search import GraphSearchService

    await repo.upsert(
        entities=[
            {"id": "p1", "type": "Policy", "name": "Procurement", "tenant_id": 1},
            {"id": "d1", "type": "Department", "name": "Finance", "tenant_id": 1},
        ],
        relations=[
            {"source": "p1", "target": "d1", "type": "APPLIES_TO", "tenant_id": 1},
        ],
    )

    svc = GraphSearchService(repo)
    result = await svc.search(
        tenant_id=1, query="procurement", seed_entity_ids=["p1"], max_hops=2,
    )

    assert result.graph_used
    assert "Procurement" in result.context
    assert "Finance" in result.context
    assert "source" in result.context.lower()


async def test_search_service_no_seed_entities(repo) -> None:
    from policymind.graph.search import GraphSearchService

    svc = GraphSearchService(repo)
    result = await svc.search(tenant_id=1, seed_entity_ids=[], max_hops=2)

    assert not result.graph_used
    assert result.skip_reason == "no seed entities"


def test_search_ranks_by_query_match() -> None:
    """rank_paths 对 query 匹配项加分。"""
    p1 = GraphPath(
        entities=[{"id": "a", "type": "Policy", "name": "Procurement Policy", "confidence": 0.9}],
        relations=[],
    )
    p2 = GraphPath(
        entities=[{"id": "b", "type": "Policy", "name": "Travel Rules", "confidence": 0.9}],
        relations=[],
    )
    ranked = rank_paths([p1, p2], query="procurement")
    assert ranked[0].entities[0]["id"] == "a"
