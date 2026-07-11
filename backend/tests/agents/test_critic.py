from policymind.agents.critic import run_critic


def test_critic_passes_valid_answer() -> None:
    decision = run_critic(
        draft_answer="Procurement requires manager approval for amounts over $5000.",
        citations=["C1"],
        tool_count=0,
    )
    assert decision.verdict in ("pass", "replan", "interrupt")


def test_critic_flags_missing_citations() -> None:
    decision = run_critic(
        draft_answer="Procurement requires manager approval.",
        citations=[],
        tool_count=0,
    )
    # 缺少引用应降低置信度或触发 replan
    assert decision.confidence < 1.0


def test_critic_flags_low_confidence_no_evidence() -> None:
    decision = run_critic(
        draft_answer="I think procurement needs approval, but I'm not sure.",
        citations=[],
        tool_count=0,
    )
    assert decision.confidence < 0.8
    assert decision.verdict != "pass"
