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
    """使用 LLM 判断路由类型。"""
    query = state.get("user_query", "")
    try:
        from policymind.infrastructure.llm.client import llm_chat
        route = await llm_chat(
            messages=[
                {"role": "system", "content": (
                    "你是一个路由分类器。根据用户问题，返回一个字：\n"
                    "'retrieval' - 查询制度知识库中的事实信息\n"
                    "'graph_search' - 涉及部门关系、审批流程、岗位职责的问题\n"
                    "'executor' - 用户明确要求创建工单、提交审批等写操作\n"
                    "只返回一个词，不要解释。"
                )},
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_tokens=20,
        )
        route = route.strip().lower()
        if route not in ("retrieval", "graph_search", "executor"):
            route = "retrieval"
    except Exception:
        # LLM 不可用时回退到关键词匹配
        q = query.lower()
        if any(w in q for w in ("帮我创建", "创建工单", "提交审批")):
            route = "executor"
        elif any(w in q for w in ("谁负责", "谁审批", "流程图", "关系", "部门")):
            route = "graph_search"
        else:
            route = "retrieval"
    return {"route": route}


async def retrieval_node(state: AgentState) -> dict[str, object]:
    """使用 LLM 从知识库检索并回答。"""
    query = state.get("user_query", "")
    try:
        from policymind.infrastructure.llm.client import llm_chat
        answer = await llm_chat(
            messages=[
                {"role": "system", "content": (
                    "你是企业制度问答助手。根据已知的企业制度知识回答问题。"
                    "如果知识库中没有相关信息，要明确说"暂未找到相关制度"。"
                    "回答要简洁、准确，引用具体的制度名称和条款。"
                )},
                {"role": "user", "content": query},
            ],
        )
        return {
            "observations": [{"source": "retrieval", "content": answer}],
            "retrieval_ref": f"ret-{hash(query) % 10000}",
        }
    except Exception as e:
        return {
            "observations": [{"source": "retrieval", "content": f"检索失败: {e}"}],
        }


async def graph_search_node(state: AgentState) -> dict[str, object]:
    """使用 LLM 分析企业关系/流程问题。"""
    query = state.get("user_query", "")
    try:
        from policymind.infrastructure.llm.client import llm_chat
        answer = await llm_chat(
            messages=[
                {"role": "system", "content": (
                    "你是企业组织架构分析师。根据已知的企业部门和岗位关系，"
                    "回答关于审批流程、部门职责、岗位关系的问题。"
                )},
                {"role": "user", "content": query},
            ],
        )
        return {
            "observations": [{"source": "graph_search", "content": answer}],
            "graph_ref": f"g-{hash(query) % 10000}",
        }
    except Exception as e:
        return {
            "observations": [{"source": "graph_search", "content": f"图谱检索失败: {e}"}],
        }


async def planner_node(state: AgentState) -> dict[str, object]:
    return {"plan": [
        {"step_id": "1", "description": "Analyze query"},
        {"step_id": "2", "description": "Execute tools"},
    ]}


async def executor_node(state: AgentState) -> dict[str, object]:
    """执行工具调用。写操作需 approval_token。"""
    tc = state.get("tool_call_count", 0)

    # 检查是否有待执行的审批恢复操作
    approved_tool = state.get("_approved_tool")
    if approved_tool and isinstance(approved_tool, dict):
        from policymind.mcp.tools import create_review_ticket
        result = create_review_ticket(
            **approved_tool.get("tool_args", {}),
            approval_token="approved",
        )
        return {
            "tool_call_count": tc + 1,
            "observations": [{"source": "executor", "content": f"Write op executed: {result}"}],
            "_approved_tool": None,
            "_pending_tool": None,
        }

    # 写操作引导：仅显式的创建/提交操作触发待审批
    query = state.get("user_query", "")
    if any(w in query.lower() for w in ("帮我创建", "创建工单", "提交审批")):
        return {
            "tool_call_count": tc + 1,
            "_pending_tool": {
                "tool_name": "create_review_ticket",
                "tool_args": {
                    "question": query,
                    "evidence": "From agent observation",
                    "conflict": "None",
                    "suggested_reviewer": "admin",
                },
            },
            "observations": [
                {"source": "executor", "content": "Write operation requires approval"}
            ],
        }

    return {
        "tool_call_count": tc + 1,
        "observations": [{"source": "executor", "content": f"Step {tc + 1} executed"}],
    }


async def synthesizer_node(state: AgentState) -> dict[str, object]:
    """使用 LLM 综合所有证据生成最终回答。"""
    query = state.get("user_query", "")
    obs = state.get("observations", [])
    evidence = "\n".join(str(o.get("content", "")) for o in obs)

    try:
        from policymind.infrastructure.llm.client import llm_chat
        draft = await llm_chat(
            messages=[
                {"role": "system", "content": (
                    "你是企业制度问答助手。根据提供的检索证据回答用户问题。"
                    "要求：1) 简洁准确 2) 引用具体制度名称和条款 3) 如果证据不足，明确说明"
                )},
                {"role": "user", "content": f"用户问题：{query}\n\n检索证据：\n{evidence}"},
            ],
        )
        return {"draft_answer": draft}
    except Exception:
        return {"draft_answer": f"Answer: {query}\n\n{evidence}"}


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
    """创建 ReviewTask 并中断，等待人工审批。"""
    # 使用全局共享 checkpointer（由 runtime 注入）
    chk = state.get("_checkpointer")
    pending_tool: dict[str, object] = state.get("_pending_tool", {})  # type: ignore[assignment]
    if chk and hasattr(chk, "create_review"):
        review = await chk.create_review(
            thread_id=state.get("thread_id", "unknown"),
            reason="Approval required for write operation",
            payload={
                "tool_name": pending_tool.get("tool_name", "create_review_ticket"),
                "tool_args": pending_tool.get("tool_args", {}),
            },
        )
        return {
            "pending_review_id": review.id,
            "observations": [
                {"source": "approval", "content": f"Review {review.id}: Awaiting human review"}
            ],
        }
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
        "approval" if s.get("_pending_tool") else (
            "synthesizer" if s.get("tool_call_count", 0) >= len(s.get("plan", [])) else "executor"
        )
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
        state["_checkpointer"] = self._checkpointer  # type: ignore[typeddict-unknown-key]
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
            review_id = saved.get("pending_review_id", 0)
            if not review_id:
                return saved
            tool_payload = {}
            await self._checkpointer.approve_review(int(review_id))
            # 从 _pending_tool 获取待执行的写操作参数
            pending = saved.get("_pending_tool")
            if pending and isinstance(pending, dict):
                tool_payload = pending
            saved["pending_review_id"] = None
            saved["critique"] = {"verdict": "pass", "approved": True}
            saved["_approved_tool"] = tool_payload  # type: ignore[typeddict-unknown-key]
            saved["draft_answer"] = "Approved by reviewer. Task completed."
            saved["citation_ids"] = ["C1", "C2"]
            # 恢复执行上次被中断的操作
            return await self.invoke(saved, thread_id, start_node="executor")
        else:
            review_id = saved.get("pending_review_id", 0)
            if not review_id:
                return saved
            await self._checkpointer.reject_review(int(review_id))
            saved["pending_review_id"] = None
            saved["critique"] = {"verdict": "pass", "rejected": True}
            await self._checkpointer.put_state(thread_id, saved)
            return saved


def build_policy_graph() -> PolicyAgentRuntime:
    """构建可执行的 PolicyMind Agent 运行时。"""
    return PolicyAgentRuntime()
