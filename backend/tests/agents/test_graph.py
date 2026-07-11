from policymind.agents.graph import (
    build_policy_graph,
    critic_node,
    route_after_critic,
    supervisor_node,
    synthesizer_node,
)
from policymind.agents.state import AgentState


def test_graph_has_required_nodes() -> None:
    graph = build_policy_graph()
    nodes = graph["nodes"]
    assert "supervisor" in nodes
    assert "retrieval" in nodes
    assert "graph_search" in nodes
    assert "planner" in nodes
    assert "executor" in nodes
    assert "synthesizer" in nodes
    assert "critic" in nodes
    assert "approval" in nodes


async def test_supervisor_routes_retrieval() -> None:
    state: AgentState = {"user_query": "What is procurement policy?", "messages": []}
    updated = await supervisor_node(state)
    assert updated.get("route") == "retrieval"


async def test_supervisor_routes_graph_for_relationship() -> None:
    state: AgentState = {
        "user_query": "Who is responsible for the procurement process?",
        "messages": [],
    }
    updated = await supervisor_node(state)
    assert updated.get("route") == "graph_search"


async def test_supervisor_routes_executor_for_tool_query() -> None:
    state: AgentState = {"user_query": "approval chain for purchase of 7000", "messages": []}
    updated = await supervisor_node(state)
    assert updated.get("route") == "executor"


def test_critic_passes_good_answer() -> None:
    state: AgentState = {
        "draft_answer": "Procurement requires manager approval for amounts over $5000.",
        "citation_ids": ["C1", "C2"],
        "messages": [],
    }
    result = route_after_critic(state)
    assert result == "__end__"


async def test_critic_interrupts_uncertain_answer() -> None:
    state: AgentState = {
        "draft_answer": "I think maybe procurement might need approval.",
        "citation_ids": [],
        "tool_call_count": 0,
        "retry_count": 0,
        "messages": [],
    }
    # 先跑 critic_node 设置 verdict
    updated = await critic_node(state)
    critique = updated.get("critique", {})
    assert isinstance(critique, dict)
    assert "verdict" in critique
    # 使用更新后的 state
    state["critique"] = critique
    result = route_after_critic(state)
    assert result == "approval"


async def test_synthesizer_combines_observations() -> None:
    state: AgentState = {
        "user_query": "Test query",
        "observations": [
            {"source": "retrieval", "content": "Doc says X."},
            {"source": "executor", "content": "Tool says Y."},
        ],
        "messages": [],
    }
    result = await synthesizer_node(state)
    assert "Doc says X" in result["draft_answer"]
    assert "Tool says Y" in result["draft_answer"]


async def test_critic_node_verdict() -> None:
    state: AgentState = {
        "draft_answer": "The policy states that procurement needs approval.",
        "citation_ids": ["C1"],
        "tool_call_count": 0,
        "retry_count": 0,
        "messages": [],
    }
    result = await critic_node(state)
    critique = result.get("critique", {})
    assert isinstance(critique, dict)
    assert "verdict" in critique
