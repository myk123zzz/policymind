"""Review API — HITL 审核任务管理，共享 Agent runtime checkpointer。"""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.agents.graph import PolicyAgentRuntime
from policymind.auth.dependencies import RequestContext, get_current_context
from policymind.infrastructure.postgres.session import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


def _get_runtime(request: Request) -> PolicyAgentRuntime:
    return request.app.state.agent_runtime  # type: ignore[no-any-return]


@router.get("")
async def list_reviews(
    request: Request,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
    runtime: PolicyAgentRuntime = Depends(_get_runtime),
) -> list[dict[str, object]]:
    """列出当前内存 checkpointer 中的待处理审核。"""
    chk = runtime._checkpointer
    reviews: list[dict[str, object]] = []
    for rid_str, review in chk._reviews.items():
        if review.status == "pending":
            reviews.append({
                "id": review.id,
                "thread_id": review.thread_id,
                "reason": review.reason,
                "status": review.status,
            })
    return reviews


@router.get("/{review_id}")
async def get_review(
    review_id: int,
    request: Request,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
    runtime: PolicyAgentRuntime = Depends(_get_runtime),
) -> dict[str, object]:
    chk = runtime._checkpointer
    review = chk._reviews.get(str(review_id))
    if review:
        return {
            "id": review.id, "thread_id": review.thread_id,
            "reason": review.reason, "status": review.status,
        }
    return {"error": "Review not found"}


@router.post("/{review_id}/approve")
async def approve_review(
    review_id: int,
    request: Request,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
    runtime: PolicyAgentRuntime = Depends(_get_runtime),
) -> dict[str, object]:
    await runtime._checkpointer.approve_review(review_id, reviewer_id=ctx.user_id)
    return {"id": review_id, "status": "approved"}


@router.post("/{review_id}/reject")
async def reject_review(
    review_id: int,
    request: Request,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
    runtime: PolicyAgentRuntime = Depends(_get_runtime),
) -> dict[str, object]:
    await runtime._checkpointer.reject_review(review_id, comment="Rejected by reviewer")
    return {"id": review_id, "status": "rejected"}
