"""PolicyMind Agent Graph — 固定拓扑 LangGraph 状态机。

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

logger = logging.getLogger(__name__)

RouteType = Literal[
    "retrieval", "graph_search", "planner", "executor",
    "synthesizer", "critic", "approval", "__end__",
]


async def supervisor_node(state: AgentState) -> dict[str, object]:
    """路由判断：简单知识→retrieval，关系问题→graph_search，复杂→planner，工具→executor。"""
    query = state.get("user_query", "").lower()

    if any(w in query for w in ("审批", "材料", "员工", "工单", "approval chain", "approval")):
        route = "executor"
    elif any(w in query for w in (
        "谁负责", "负责", "属于哪个部门", "流程", "步骤", "关系", "区别",
        "responsible", "process",
    )):
        route = "graph_search"
    elif len(query) > 100 or any(w in query for w in ("复杂", "多个步骤", "综合")):
        route = "planner"
    else:
        route = "retrieval"

    return {"route": route}


async def retrieval_node(state: AgentState) -> dict[str, object]:
    """检索节点：从知识库获取相关文档片段。"""
    query = state.get("user_query", "")
    return {
        "observations": [{"source": "retrieval", "content": f"Retrieved context for: {query}"}],
        "retrieval_ref": f"{query[:20]}...",
    }


async def graph_search_node(state: AgentState) -> dict[str, object]:
    """图谱搜索节点：查实体关系路径。"""
    query = state.get("user_query", "")
    return {
        "observations": [{"source": "graph_search", "content": f"Graph paths for: {query}"}],
        "graph_ref": f"graph-{hash(query) % 10000}",
    }


async def planner_node(state: AgentState) -> dict[str, object]:
    """规划节点：拆解复杂任务为步骤序列。"""
    return {
        "plan": [
            {"step_id": "1", "description": "Analyze query", "tool": "retrieval"},
            {"step_id": "2", "description": "Execute tool calls", "tool": "executor"},
        ],
    }


async def executor_node(state: AgentState) -> dict[str, object]:
    """执行节点：运行工具调用。"""
    tc = state.get("tool_call_count", 0)
    return {
        "tool_call_count": tc + 1,
        "observations": [{"source": "executor", "content": "Tool executed"}],
    }


async def synthesizer_node(state: AgentState) -> dict[str, object]:
    """合成节点：汇总检索/图谱/工具结果，生成回答。"""
    observations = state.get("observations", [])
    query = state.get("user_query", "")
    parts = [f"Answer to: {query}"]
    for obs in observations:
        parts.append(str(obs.get("content", "")))
    return {"draft_answer": "\n".join(parts)}


async def critic_node(state: AgentState) -> dict[str, object]:
    """Critic 节点：检查回答质量，决定 pass/replan/approval。"""
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
    """审批节点：暂停等待人工决策（HITL interrupt）。"""
    return {
        "pending_review_id": 1,
        "observations": [{"source": "approval", "content": "Awaiting human review"}],
    }


def route_after_supervisor(state: AgentState) -> RouteType:
    return state.get("route", "retrieval")  # type: ignore[return-value]


def route_after_critic(state: AgentState) -> RouteType:
    critique = state.get("critique", {}) or {}
    verdict = critique.get("verdict", "pass")
    if verdict == "replan":
        return "planner"
    if verdict == "interrupt":
        return "approval"
    # 注：route_after_critic 不直接读取 draft_answer，
    # verdict 由 critic_node 设置后传入 state
    return "__end__"


def route_after_planner(state: AgentState) -> RouteType:
    plan = state.get("plan", [])
    if plan:
        return "executor"
    return "synthesizer"


def route_after_executor(state: AgentState) -> RouteType:
    plan = state.get("plan", [])
    tc = state.get("tool_call_count", 0)
    if tc < len(plan):
        return "executor"
    return "synthesizer"


def route_after_approval(state: AgentState) -> RouteType:
    pending = state.get("pending_review_id")
    if pending:
        return "__end__"  # 等待 resume
    return "executor"


def build_policy_graph() -> dict[str, object]:
    """构建 Agent 拓扑结构定义。返回节点和边的元数据，供执行引擎使用。"""
    return {
        "nodes": [
            "supervisor", "retrieval", "graph_search", "planner",
            "executor", "synthesizer", "critic", "approval",
            "normalize",
        ],
        "edges": {
            "supervisor": route_after_supervisor,
            "retrieval": lambda _: "synthesizer",
            "graph_search": lambda _: "synthesizer",
            "planner": route_after_planner,
            "executor": route_after_executor,
            "synthesizer": lambda _: "critic",
            "critic": route_after_critic,
            "approval": route_after_approval,
        },
    }
