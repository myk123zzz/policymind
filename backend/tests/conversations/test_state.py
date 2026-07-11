def test_agent_state_structure() -> None:
    from policymind.agents.state import AgentState

    state: AgentState = {
        "messages": [],
        "request_context": {"tenant_id": 1, "user_id": 1, "role": "employee"},
        "thread_id": "thread-1",
        "user_query": "What is the procurement policy?",
        "normalized_query": "procurement policy",
        "route": "",
        "plan": [],
        "observations": [],
        "retrieval_ref": None,
        "graph_ref": None,
        "citation_ids": [],
        "draft_answer": "",
        "critique": None,
        "retry_count": 0,
        "tool_call_count": 0,
        "pending_review_id": None,
    }
    assert state["user_query"] == "What is the procurement policy?"
    assert state["retry_count"] == 0
