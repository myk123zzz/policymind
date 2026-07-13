"""Chat API — SSE 流式 Agent 对话。"""

import json
import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.agents.graph import build_policy_graph
from policymind.agents.state import AgentState
from policymind.auth.dependencies import RequestContext, get_current_context
from policymind.infrastructure.postgres.session import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatCommand(BaseModel):
    query: str
    thread_id: str | None = None


class ReviewDecision(BaseModel):
    decision: str  # "approve" | "reject"
    comment: str = ""


SSE_EVENTS = [
    "routing", "plan", "tool_call", "tool_result", "retrieval",
    "graph_path", "content", "citation", "review_required", "error", "done",
]


async def _sse_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/chat/stream")
async def chat_stream(
    body: ChatCommand,
    request: Request,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
) -> object:
    """SSE 流式 Agent 对话。只发送公开事件，不暴露隐藏推理。"""
    import uuid

    thread_id = body.thread_id or f"thread-{uuid.uuid4().hex[:8]}"

    async def event_generator():  # type: ignore[no-untyped-def]
        runtime = build_policy_graph()
        state: AgentState = {
            "messages": [],
            "request_context": {
                "tenant_id": ctx.tenant_id,
                "user_id": ctx.user_id,
                "role": ctx.role,
            },
            "thread_id": thread_id,
            "user_query": body.query,
            "normalized_query": body.query.lower(),
            "route": "",
            "plan": [],
            "observations": [],
            "citation_ids": [],
            "retry_count": 0,
            "tool_call_count": 0,
        }

        # 1. Routing event
        yield await _sse_event("routing", {"status": "analyzing"})

        # 2. Execute agent
        try:
            result = await runtime.invoke(state, thread_id)

            # Send retrieval/graph events if present
            if result.get("retrieval_ref"):
                yield await _sse_event("retrieval", {"ref": str(result["retrieval_ref"])})
            if result.get("graph_ref"):
                yield await _sse_event("graph_path", {"ref": str(result["graph_ref"])})

            # Send content
            draft = result.get("draft_answer", "")
            if draft:
                yield await _sse_event("content", {"text": draft})

            # Send citations if any
            cids = result.get("citation_ids", [])
            if cids:
                yield await _sse_event("citation", {"ids": [str(c) for c in cids]})

            # Check for review_required
            if result.get("pending_review_id"):
                yield await _sse_event(
                    "review_required",
                    {"review_id": result.get("pending_review_id", 0)},
                )

            yield await _sse_event("done", {"thread_id": thread_id})
        except Exception as e:
            logger.exception("Chat stream error")
            yield await _sse_event("error", {"message": str(e)})

    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        event_generator(),  # type: ignore[no-untyped-call]
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/{thread_id}/resume")
async def chat_resume(  # type: ignore[no-untyped-def]
    thread_id: str,
    body: ReviewDecision,
    request: Request,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
):
    """恢复 HITL 中断的对话。"""
    runtime = build_policy_graph()
    result = await runtime.resume(thread_id, body.decision)
    if result is None:
        return {"error": "Thread not found"}
    return {
        "thread_id": thread_id,
        "status": "completed" if not result.get("pending_review_id") else "pending",
        "draft_answer": result.get("draft_answer", ""),
    }
