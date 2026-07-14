"""Graph API — 知识图谱查询，从共享 repo 读取真实数据。"""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.auth.dependencies import RequestContext, get_current_context
from policymind.graph.repository import MemoryGraphRepository
from policymind.infrastructure.postgres.session import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


def _get_repo(request: Request) -> MemoryGraphRepository:
    return request.app.state.graph_repo  # type: ignore[no-any-return]


@router.get("/subgraph")
async def get_subgraph(
    seed_ids: str = "",
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
    repo: MemoryGraphRepository = Depends(_get_repo),
) -> dict[str, object]:
    ids = [s.strip() for s in seed_ids.split(",") if s.strip()]
    paths = await repo.search_paths(
        tenant_id=ctx.tenant_id, seed_entity_ids=ids, max_hops=2, limit=10,
    )
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    seen = set()
    for path in paths:
        for e in path.entities:
            eid = str(e.get("id", ""))
            if eid not in seen:
                seen.add(eid)
                nodes.append({
                    "id": eid, "type": str(e.get("type", "")),
                    "name": str(e.get("name", "")),
                })
        for r in path.relations:
            edges.append({
                "source": str(r.get("source", "")),
                "target": str(r.get("target", "")),
                "type": str(r.get("type", "")),
            })
    return {"nodes": nodes, "edges": edges, "seed_ids": ids}


@router.get("/entities/{entity_id}")
async def get_entity(
    entity_id: str,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
    repo: MemoryGraphRepository = Depends(_get_repo),
) -> dict[str, object]:
    entity = repo._entities.get(entity_id)
    if entity:
        return {
            "id": entity_id, "type": str(entity.get("type", "")),
            "name": str(entity.get("name", "")), "tenant_id": ctx.tenant_id,
        }
    return {"id": entity_id, "type": "Unknown", "name": "Not found"}
