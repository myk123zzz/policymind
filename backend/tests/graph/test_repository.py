import pytest_asyncio


@pytest_asyncio.fixture
async def repo():
    from policymind.graph.repository import MemoryGraphRepository

    return MemoryGraphRepository()


async def test_upsert_and_search_entities(repo) -> None:
    entities = [
        {"id": "dept-rd", "type": "Department", "name": "R&D", "tenant_id": 1},
        {"id": "role-intern", "type": "Role", "name": "Intern", "tenant_id": 1},
    ]
    relations = [
        {"source": "role-intern", "target": "dept-rd", "type": "BELONGS_TO", "tenant_id": 1},
    ]
    await repo.upsert(entities=entities, relations=relations)

    paths = await repo.search_paths(
        tenant_id=1, seed_entity_ids=["role-intern"], max_hops=2, limit=10,
    )
    assert len(paths) > 0
    assert any("dept-rd" in str(p) for p in paths)


async def test_tenant_isolation(repo) -> None:
    await repo.upsert(
        entities=[{"id": "e1", "type": "Policy", "name": "T1", "tenant_id": 1}],
        relations=[],
    )
    await repo.upsert(
        entities=[{"id": "e2", "type": "Policy", "name": "T2", "tenant_id": 2}],
        relations=[],
    )
    paths = await repo.search_paths(
        tenant_id=1, seed_entity_ids=["e1"], max_hops=1, limit=10,
    )
    assert len(paths) > 0
    # 租户 2 的实体不应出现在结果中
    for p in paths:
        assert "e2" not in str(p)


async def test_multi_hop_path(repo) -> None:
    entities = [
        {"id": "a", "type": "Policy", "name": "A", "tenant_id": 1},
        {"id": "b", "type": "Department", "name": "B", "tenant_id": 1},
        {"id": "c", "type": "Role", "name": "C", "tenant_id": 1},
    ]
    relations = [
        {"source": "a", "target": "b", "type": "APPLIES_TO", "tenant_id": 1},
        {"source": "b", "target": "c", "type": "OWNED_BY", "tenant_id": 1},
    ]
    await repo.upsert(entities=entities, relations=relations)

    paths = await repo.search_paths(
        tenant_id=1, seed_entity_ids=["a"], max_hops=2, limit=10,
    )
    # 2-hop should reach 'c'
    assert len(paths) > 0
    found_c = any("c" in str(p) for p in paths)
    assert found_c
