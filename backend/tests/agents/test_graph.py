from policymind.agents.graph import (
    build_policy_graph,
    supervisor_node,
    synthesizer_node,
)
from policymind.agents.state import AgentState


def test_runtime_builds() -> None:
    runtime = build_policy_graph()
    assert runtime is not None


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


async def test_invoke_simple_query() -> None:
    """简单检索问题走完 supervisor→retrieval→synthesizer→critic→END。"""
    runtime = build_policy_graph()
    state: AgentState = {
        "user_query": "What is the procurement policy?",
        "messages": [],
        "citation_ids": [],
        "tool_call_count": 0,
        "retry_count": 0,
    }
    result = await runtime.invoke(state, thread_id="test-thread-1")
    assert result["draft_answer"]
    assert ("critique" in result) or ("critique" in result)


async def test_invoke_approval_interrupt() -> None:
    """不确定回答触发 approval 中断。"""
    runtime = build_policy_graph()
    state: AgentState = {
        "user_query": "I think maybe probably I am not sure about the answer?",
        "messages": [],
        "citation_ids": [],
        "tool_call_count": 0,
        "retry_count": 0,
    }
    result = await runtime.invoke(state, thread_id="test-thread-2")
    assert result.get("pending_review_id") is not None


async def test_resume_after_approval() -> None:
    """批准后恢复执行到 END。"""
    runtime = build_policy_graph()
    state: AgentState = {
        "user_query": "I think maybe probably I am not sure about the answer?",
        "messages": [],
        "citation_ids": [],
        "tool_call_count": 0,
        "retry_count": 0,
    }
    interrupted = await runtime.invoke(state, thread_id="test-thread-3")
    assert interrupted.get("pending_review_id") is not None
    resumed = await runtime.resume(thread_id="test-thread-3", decision="approve")
    assert resumed is not None
    assert resumed.get("pending_review_id") is None


async def test_resume_reject() -> None:
    """拒绝后直接结束。"""
    runtime = build_policy_graph()
    state: AgentState = {
        "user_query": "I think maybe probably I am not sure about the answer?",
        "messages": [],
        "citation_ids": [],
        "tool_call_count": 0,
        "retry_count": 0,
    }
    interrupted = await runtime.invoke(state, thread_id="test-thread-5")
    assert interrupted.get("pending_review_id") is not None
    resumed = await runtime.resume(thread_id="test-thread-5", decision="reject")
    assert resumed is not None
    assert resumed.get("pending_review_id") is None
    assert resumed.get("critique", {}).get("rejected")  # type: ignore[union-attr]


async def test_resume_executes_pending_write() -> None:
    """批准后 executor_node 真实执行被拦下的写操作。"""
    runtime = build_policy_graph()
    state: AgentState = {
        "user_query": "approval review ticket for procurement",
        "messages": [],
        "citation_ids": [],
        "tool_call_count": 0,
        "retry_count": 0,
    }
    # invoke: supervisor → executor (注入 _pending_tool) → approval (HITL)
    interrupted = await runtime.invoke(state, thread_id="test-write-1")
    assert interrupted.get("pending_review_id") is not None
    assert interrupted.get("_pending_tool") is not None
    assert interrupted["_pending_tool"]["tool_name"] == "create_review_ticket"

    # 批准恢复 → executor 真实执行 create_review_ticket
    resumed = await runtime.resume(thread_id="test-write-1", decision="approve")
    assert resumed is not None
    # approved_tool consumed (只执行一次)
    assert resumed.get("_approved_tool") is None
    assert resumed.get("_pending_tool") is None
    assert resumed.get("pending_review_id") is None
    # 观测或 answer 中包含执行成功的痕迹
    draft = resumed.get("draft_answer", "")
    observations = resumed.get("observations", [])
    assert any("Write op executed" in o.get("content", "") for o in observations)
    assert "ticket-" in draft

    resumed_again = await runtime.resume(thread_id="test-write-1", decision="approve")
    assert resumed_again == resumed
    assert resumed_again.get("pending_review_id") is None


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
