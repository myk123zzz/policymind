from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class GraphPath:
    entities: list[dict[str, object]]
    relations: list[dict[str, object]]
    score: float = 0.0


class GraphRepository(Protocol):
    async def upsert(
        self,
        entities: Sequence[dict[str, object]],
        relations: Sequence[dict[str, object]],
    ) -> None: ...

    async def search_paths(
        self,
        *,
        tenant_id: int,
        seed_entity_ids: Sequence[str],
        max_hops: int,
        limit: int,
    ) -> list[GraphPath]: ...


class MemoryGraphRepository:
    """内存图谱存储，用于测试。"""

    def __init__(self) -> None:
        self._entities: dict[str, dict[str, object]] = {}
        self._relations: list[dict[str, object]] = []

    async def upsert(
        self,
        entities: Sequence[dict[str, object]],
        relations: Sequence[dict[str, object]],
    ) -> None:
        for e in entities:
            eid = str(e["id"])
            self._entities[eid] = dict(e)
        for r in relations:
            self._relations.append(dict(r))

    async def search_paths(
        self,
        *,
        tenant_id: int,
        seed_entity_ids: Sequence[str],
        max_hops: int,
        limit: int,
    ) -> list[GraphPath]:
        # BFS from seed entities
        paths: list[GraphPath] = []
        visited: set[str] = set()
        queue: list[tuple[str, list[dict[str, object]], list[dict[str, object]]]] = [
            (sid, [], []) for sid in seed_entity_ids
        ]

        for _hop in range(max_hops + 1):
            nxt: list[tuple[str, list[dict[str, object]], list[dict[str, object]]]] = []
            for node_id, ents, rels in queue:
                if node_id in visited:
                    continue
                visited.add(node_id)
                entity = self._entities.get(node_id)
                if entity is None or int(str(entity.get("tenant_id", 0))) != tenant_id:
                    continue
                new_ents = ents + [entity]

                # 检查是否已达目标实体（有出边）
                has_outgoing = False
                for r in self._relations:
                    if (
                        str(r.get("source")) == node_id
                        and int(str(r.get("tenant_id", 0))) == tenant_id
                    ):
                        target = str(r.get("target", ""))
                        has_outgoing = True
                        nxt.append((target, new_ents, rels + [r]))

                if not has_outgoing or len(new_ents) >= max_hops + 1:
                    if new_ents:
                        paths.append(GraphPath(entities=new_ents, relations=rels, score=1.0))
            queue = nxt

        # 按 paths 长度和得分排序
        paths.sort(key=lambda p: (len(p.entities), p.score), reverse=True)
        return paths[:limit]
