"""PolicyMind Agent Graph — 可执行状态机。

START → supervisor
supervisor → retrieval | graph_search | planner | executor
planner → executor
executor → executor | planner | synthesizer
retrieval → synthesizer
graph_search → synthesizer
synthesizer → critic
critic → END | approval
approval → executor | END
"""

import logging
from typing import Literal

from policymind.agents.critic import run_critic
from policymind.agents.state import AgentState
from policymind.conversations.checkpoint import MemoryCheckpointer

logger = logging.getLogger(__name__)

RouteType = Literal[
    "retrieval", "graph_search", "planner", "executor",
    "synthesizer", "critic", "approval", "__end__",
]

# --- 节点函数 ---


async def supervisor_node(state: AgentState) -> dict[str, object]:
    query = state.get("user_query", "").lower()
    if any(w in query for w in ("审批", "材料", "员工", "工单", "approval chain", "approval")):
        route = "executor"
    elif any(w in query for w in (
        "谁负责", "负责", "属于哪个部门", "流程", "步骤", "关系", "区别",
        "responsible", "process",
    )):
        route = "graph_search"
    elif len(query) > 100:
        route = "planner"
    else:
        route = "retrieval"
    return {"route": route}


async def retrieval_node(state: AgentState) -> dict[str, object]:
    query = state.get("user_query", "")
    return {
        "observations": [{"source": "retrieval", "content": f"Context for: {query}"}],
        "retrieval_ref": f"ret-{hash(query) % 10000}",
    }


async def graph_search_node(state: AgentState) -> dict[str, object]:
    query = state.get("user_query", "")
    return {
        "observations": [{"source": "graph_search", "content": f"Graph paths for: {query}"}],
        "graph_ref": f"g-{hash(query) % 10000}",
    }


async def planner_node(state: AgentState) -> dict[str, object]:
    return {"plan": [
        {"step_id": "1", "description": "Analyze query"},
        {"step_id": "2", "description": "Execute tools"},
    ]}


async def executor_node(state: AgentState) -> dict[str, object]:
    tc = state.get("tool_call_count", 0)
    return {
        "tool_call_count": tc + 1,
        "observations": [{"source": "executor", "content": f"Step {tc + 1} executed"}],
    }


async def synthesizer_node(state: AgentState) -> dict[str, object]:
    query = state.get("user_query", "")
    obs = state.get("observations", [])
    parts = [f"Answer: {query}"]
    for o in obs:
        parts.append(str(o.get("content", "")))
    return {"draft_answer": "\n".join(parts)}


async def critic_node(state: AgentState) -> dict[str, object]:
    draft = state.get("draft_answer", "")
    citations = state.get("citation_ids", [])
    tc = state.get("tool_call_count", 0)
    retry = state.get("retry_count", 0)
    decision = run_critic(draft, citations, tc)
    if decision.verdict == "replan" and retry < 2:
        return {"critique": {"verdict": "replan"}, "retry_count": retry + 1}
    if decision.verdict == "interrupt":
        return {"critique": {"verdict": "interrupt", "reason": decision.reason}}
    return {"critique": {"verdict": "pass", "confidence": decision.confidence}}


async def approval_node(state: AgentState) -> dict[str, object]:
    return {
        "pending_review_id": 1,
        "observations": [{"source": "approval", "content": "Awaiting human review"}],
    }


# --- 路由函数 ---

NODE_MAP: dict[str, object] = {
    "supervisor": supervisor_node,
    "retrieval": retrieval_node,
    "graph_search": graph_search_node,
    "planner": planner_node,
    "executor": executor_node,
    "synthesizer": synthesizer_node,
    "critic": critic_node,
    "approval": approval_node,
}

EDGE_MAP: dict[str, object] = {
    "supervisor": lambda s: s.get("route", "retrieval"),
    "retrieval": lambda _: "synthesizer",
    "graph_search": lambda _: "synthesizer",
    "planner": lambda s: "executor" if s.get("plan") else "synthesizer",
    "executor": lambda s: (
        "synthesizer" if s.get("tool_call_count", 0) >= len(s.get("plan", [])) else "executor"
    ),
    "synthesizer": lambda _: "critic",
    "critic": lambda s: (
        {
            "replan": "planner",
            "interrupt": "approval",
        }.get(
            str((s.get("critique") or {}).get("verdict")), "__end__"
        )
    ),
    "approval": lambda s: "__end__" if s.get("pending_review_id") else "executor",
}


# --- 可执行 Runtime ---

class PolicyAgentRuntime:
    """最小可执行 Agent 状态机，支持 interrupt/resume。"""

    def __init__(self, checkpointer: MemoryCheckpointer | None = None) -> None:
        self._checkpointer = checkpointer or MemoryCheckpointer()

    async def invoke(
        self, state: AgentState, thread_id: str,
        start_node: str = "supervisor",
    ) -> AgentState:
        """执行 Agent 图，直到 END 或 interrupt。"""
        current_node = start_node
        state["thread_id"] = thread_id
        max_steps = 20

        for _step in range(max_steps):
            if current_node == "__end__":
                break

            # Execute current node
            node_fn = NODE_MAP.get(current_node)
            if node_fn:
                updates = await node_fn(state)  # type: ignore[operator]
                for k, v in updates.items():
                    state[k] = v  # type: ignore[literal-required]

            # Check for HITL interrupt after execution
            if current_node == "approval":
                await self._checkpointer.put_state(thread_id, state)
                break

            # Route to next node
            router = EDGE_MAP.get(current_node)
            if router:
                next_node = router(state)  # type: ignore[operator]
                current_node = next_node
            else:
                break

        await self._checkpointer.put_state(thread_id, state)
        return state

    async def resume(self, thread_id: str, decision: str) -> AgentState | None:
        """恢复暂停的 Agent 执行（HITL approve/reject）。"""
        saved = await self._checkpointer.get_state(thread_id)
        if not saved:
            return None

        if decision == "approve":
            saved["pending_review_id"] = None
            saved["critique"] = {"verdict": "pass", "approved": True}
            saved["draft_answer"] = "Approved by reviewer. Task completed."
            saved["citation_ids"] = ["C1", "C2"]
            return await self.invoke(saved, thread_id, start_node="executor")
        else:
            # Rejected: end the graph
            saved["pending_review_id"] = None
            saved["critique"] = {"verdict": "pass", "rejected": True}
            await self._checkpointer.put_state(thread_id, saved)
            return saved


def build_policy_graph() -> PolicyAgentRuntime:
    """构建可执行的 PolicyMind Agent 运行时。"""
    return PolicyAgentRuntime()
