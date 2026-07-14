"""Chat API — SSE 流式 Agent 对话。"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.agents.graph import PolicyAgentRuntime
from policymind.agents.state import AgentState
from policymind.auth.dependencies import RequestContext, get_current_context
from policymind.infrastructure.postgres.session import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatCommand(BaseModel):
    query: str
    thread_id: str | None = None


class ReviewDecision(BaseModel):
    decision: str
    comment: str = ""


def _get_runtime(request: Request) -> PolicyAgentRuntime:
    """从 app.state 获取共享 runtime。"""
    return request.app.state.agent_runtime  # type: ignore[no-any-return]


async def _sse_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/chat/stream")
async def chat_stream(
    body: ChatCommand,
    request: Request,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
    runtime: PolicyAgentRuntime = Depends(_get_runtime),
) -> object:
    thread_id = body.thread_id or f"thread-{uuid.uuid4().hex[:8]}"

    async def event_generator():  # type: ignore[no-untyped-def]
        state: AgentState = {
            "messages": [],
            "request_context": {
                "tenant_id": ctx.tenant_id, "user_id": ctx.user_id, "role": ctx.role,
            },
            "thread_id": thread_id,
            "user_query": body.query,
            "normalized_query": body.query.lower(),
            "route": "", "plan": [], "observations": [],
            "citation_ids": [], "retry_count": 0, "tool_call_count": 0,
        }
        yield await _sse_event("routing", {"status": "analyzing"})
        try:
            result = await runtime.invoke(state, thread_id)
            if result.get("retrieval_ref"):
                yield await _sse_event("retrieval", {"ref": str(result["retrieval_ref"])})
            if result.get("graph_ref"):
                yield await _sse_event("graph_path", {"ref": str(result["graph_ref"])})
            draft = result.get("draft_answer", "")
            if draft:
                yield await _sse_event("content", {"text": draft})
            cids = result.get("citation_ids", [])
            if cids:
                yield await _sse_event("citation", {"ids": [str(c) for c in cids]})
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
async def chat_resume(
    thread_id: str,
    body: ReviewDecision,
    request: Request,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
    runtime: PolicyAgentRuntime = Depends(_get_runtime),
) -> dict[str, object]:
    result = await runtime.resume(thread_id, body.decision)
    if result is None:
        return {"error": "Thread not found"}
    return {
        "thread_id": thread_id,
        "status": "completed" if not result.get("pending_review_id") else "pending",
        "draft_answer": result.get("draft_answer", ""),
    }
