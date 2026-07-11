from collections.abc import Sequence
from dataclasses import dataclass

from policymind.graph.path_ranker import rank_paths
from policymind.graph.repository import GraphPath, GraphRepository


@dataclass(slots=True)
class GraphSearchResult:
    paths: list[GraphPath]
    seed_entity_ids: list[str]
    context: str
    graph_used: bool = True
    skip_reason: str = ""


class GraphSearchService:
    """Local Graph Search：Chunk → 种子实体 → 路径 → 评分 → 带来源上下文。"""

    def __init__(self, repository: GraphRepository) -> None:
        self._repo = repository

    async def search(
        self,
        *,
        tenant_id: int,
        query: str = "",
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

        # 路径评分排序
        ranked = rank_paths(paths, query=query)[:limit]
        context = self._build_context(ranked)

        return GraphSearchResult(
            paths=ranked,
            seed_entity_ids=list(seed_entity_ids),
            context=context,
        )

    @staticmethod
    def _build_context(paths: Sequence[GraphPath]) -> str:
        lines: list[str] = []
        for i, path in enumerate(paths, 1):
            ents = " -> ".join(
                f"{str(e.get('type', '?'))}:{str(e.get('name', e.get('id', '')))}"
                for e in path.entities
            )
            rels = ", ".join(str(r.get("type", "?")) for r in path.relations)
            src_info = ""
            for e in path.entities:
                chunk = e.get("source_chunk_id", "")
                ver = e.get("source_document_version_id", "")
                if chunk:
                    src_info += f"[chunk:{chunk}, ver:{ver}] "
                break
            lines.append(
                f"Path {i} | entities: {ents} | relations: {rels} | sources: {src_info.strip()}"
            )
        return "\n".join(lines)
