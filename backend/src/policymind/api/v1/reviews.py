"""Review API — HITL 审核任务管理。"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.auth.dependencies import RequestContext, get_current_context
from policymind.infrastructure.postgres.session import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


@router.get("")
async def list_reviews(
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, object]]:
    """列出当前租户的待处理审核任务。"""
    return []


@router.get("/{review_id}")
async def get_review(
    review_id: int,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    return {"id": review_id, "status": "pending", "reason": "Write operation approval"}


@router.post("/{review_id}/approve")
async def approve_review(
    review_id: int,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    from policymind.agents.graph import build_policy_graph

    runtime = build_policy_graph()
    # Save approval in checkpointer
    await runtime._checkpointer.approve_review(review_id)
    return {"id": review_id, "status": "approved"}


@router.post("/{review_id}/reject")
async def reject_review(
    review_id: int,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    from policymind.agents.graph import build_policy_graph

    runtime = build_policy_graph()
    await runtime._checkpointer.reject_review(review_id, "Rejected by reviewer")
    return {"id": review_id, "status": "rejected"}
