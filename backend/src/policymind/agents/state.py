from typing import TypedDict


class AgentState(TypedDict, total=False):
    """LangGraph Agent 状态，序列化到 Checkpoint。"""

    messages: list[dict[str, object]]
    request_context: dict[str, object]
    thread_id: str
    user_query: str
    normalized_query: str
    route: str
    plan: list[dict[str, object]]
    observations: list[dict[str, object]]
    retrieval_ref: str | None
    graph_ref: str | None
    citation_ids: list[str]
    draft_answer: str
    critique: dict[str, object] | None
    retry_count: int
    tool_call_count: int
    pending_review_id: int | None
