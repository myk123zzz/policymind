"""Graph API — 知识图谱查询。"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.auth.dependencies import RequestContext, get_current_context
from policymind.infrastructure.postgres.session import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


@router.get("/subgraph")
async def get_subgraph(
    seed_ids: str = "",
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    return {"nodes": [], "edges": [], "seed_ids": seed_ids.split(",") if seed_ids else []}


@router.get("/entities/{entity_id}")
async def get_entity(
    entity_id: str,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    return {"id": entity_id, "type": "Policy", "name": "Unknown", "tenant_id": ctx.tenant_id}
