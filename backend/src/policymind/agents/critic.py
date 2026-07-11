import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CriticDecision:
    verdict: str  # "pass" | "replan" | "interrupt"
    confidence: float
    reason: str = ""


def run_critic(
    draft_answer: str,
    citations: list[str],
    tool_count: int,
) -> CriticDecision:
    """Critic 检查：引用存在性、置信度、是否需要人工审核。"""
    confidence = 0.9

    # 检查引用
    if not citations:
        confidence -= 0.3
    if len(draft_answer) < 20:
        confidence -= 0.2

    # 检查不确定性语言
    uncertain_markers = [
        "I think", "probably", "maybe", "not sure", "might be",
        "could be", "possibly",
    ]
    for marker in uncertain_markers:
        if marker.lower() in draft_answer.lower():
            confidence -= 0.15
            break

    # 置信度过低 → HITL
    if confidence < 0.5:
        return CriticDecision(
            verdict="interrupt", confidence=confidence, reason="Very low confidence"
        )

    # 缺少引用 → replan
    if not citations and confidence < 0.7:
        return CriticDecision(verdict="replan", confidence=confidence, reason="Missing citations")

    # 无引用且低置信度 → interrupt
    if not citations and confidence < 0.5:
        return CriticDecision(verdict="interrupt", confidence=confidence, reason="No evidence")

    return CriticDecision(verdict="pass", confidence=confidence)
