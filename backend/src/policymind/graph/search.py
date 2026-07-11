from collections.abc import Sequence
from dataclasses import dataclass

from policymind.graph.repository import GraphPath, GraphRepository


@dataclass(slots=True)
class GraphSearchResult:
    paths: list[GraphPath]
    seed_entity_ids: list[str]
    context: str
    graph_used: bool = True
    skip_reason: str = ""


class GraphSearchService:
    """Local Graph Search：Chunk → 种子实体 → 路径 → 排序 → 上下文。"""

    def __init__(self, repository: GraphRepository) -> None:
        self._repo = repository

    async def search(
        self,
        *,
        tenant_id: int,
        seed_entity_ids: Sequence[str],
        max_hops: int = 2,
        limit: int = 10,
    ) -> GraphSearchResult:
        if not seed_entity_ids:
            return GraphSearchResult(
                paths=[], seed_entity_ids=[],
                context="", graph_used=False,
                skip_reason="no seed entities",
            )

        paths = await self._repo.search_paths(
            tenant_id=tenant_id,
            seed_entity_ids=seed_entity_ids,
            max_hops=max_hops,
            limit=limit,
        )

        if not paths:
            return GraphSearchResult(
                paths=[], seed_entity_ids=list(seed_entity_ids),
                context="", graph_used=False,
                skip_reason="no paths found",
            )

        context = self._build_context(paths)
        return GraphSearchResult(
            paths=paths,
            seed_entity_ids=list(seed_entity_ids),
            context=context,
        )

    @staticmethod
    def _build_context(paths: Sequence[GraphPath]) -> str:
        lines: list[str] = []
        for i, path in enumerate(paths, 1):
            ents = " -> ".join(
                f"{e.get('type', '?')}:{e.get('name', e.get('id', ''))}"
                for e in path.entities
            )
            rels = ", ".join(
                f"{r.get('type', '?')}"
                for r in path.relations
            )
            lines.append(f"Path {i}: {ents} | relations: {rels}")
        return "\n".join(lines)
