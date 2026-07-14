"""评测 Runner：加载数据集，逐题执行，汇总指标。"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from policymind.agents.graph import build_policy_graph
from policymind.agents.state import AgentState
from policymind.evaluation.metrics import (
    required_fact_coverage,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GoldenCase:
    id: str
    category: str
    question: str
    required_facts: list[str] = field(default_factory=list)
    expected_document_versions: list[str] = field(default_factory=list)
    expected_pages: list[int] = field(default_factory=list)
    expected_route: str = "retrieval"
    expected_tools: list[str] = field(default_factory=list)
    expected_graph_edges: list[str] = field(default_factory=list)
    should_refuse: bool = False


@dataclass(slots=True)
class CaseResult:
    case_id: str
    category: str
    question: str
    actual_route: str = ""
    actual_answer: str = ""
    routing_correct: bool = False
    fact_coverage: float = 0.0
    citation_precision: float = 0.0
    graph_path_accuracy: float = 0.0
    mrr: float = 0.0
    refusal_correct: bool = False
    latency_ms: float = 0.0
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EvaluationReport:
    dataset_version: str
    total_cases: int
    routing_accuracy: float
    fact_coverage: float
    citation_precision: float
    graph_path_accuracy: float
    mrr: float
    refusal_accuracy: float
    avg_latency_ms: float
    case_results: list[CaseResult]
    model_config: dict[str, str] = field(default_factory=dict)
    prompt_version: str = "v1"


class EvaluationRunner:
    def __init__(self, dataset_path: str) -> None:
        self.dataset_path = Path(dataset_path)
        self.runtime = build_policy_graph()

    def load_dataset(self) -> list[GoldenCase]:
        cases: list[GoldenCase] = []
        with open(self.dataset_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    cases.append(GoldenCase(**data))
        return cases

    async def run_case(self, case: GoldenCase) -> CaseResult:
        start = time.perf_counter()
        result = CaseResult(case_id=case.id, category=case.category, question=case.question)

        try:
            state: AgentState = {
                "messages": [],
                "user_query": case.question,
                "normalized_query": case.question.lower(),
                "citation_ids": [],
                "tool_call_count": 0,
                "retry_count": 0,
            }
            agent_result = await self.runtime.invoke(state, f"eval-{case.id}")

            result.actual_route = agent_result.get("route", "retrieval")
            result.actual_answer = agent_result.get("draft_answer", "")
            result.routing_correct = result.actual_route == case.expected_route
            result.fact_coverage = required_fact_coverage(
                result.actual_answer, case.required_facts
            )

            # Refusal check
            if case.should_refuse:
                refusal_markers = [
                    "cannot", "not able", "don't have", "do not have",
                    "unable", "outside", "not within", "not covered",
                ]
                refused = any(
                    m in result.actual_answer.lower() for m in refusal_markers
                ) or len(result.actual_answer) < 50
                result.refusal_correct = refused
            else:
                result.refusal_correct = True

        except Exception as e:
            result.errors.append(str(e))

        result.latency_ms = (time.perf_counter() - start) * 1000
        return result

    async def run(self) -> EvaluationReport:
        cases = self.load_dataset()
        results: list[CaseResult] = []

        for case in cases:
            r = await self.run_case(case)
            results.append(r)

        total = len(results)
        routing_correct = sum(1 for r in results if r.routing_correct)
        refusal_total = sum(1 for r in results if r.refusal_correct is not None)
        refusal_correct_count = sum(
            1 for r in results if r.refusal_correct and r.refusal_correct is not None
        )

        return EvaluationReport(
            dataset_version="golden_v1",
            total_cases=total,
            routing_accuracy=routing_correct / total if total > 0 else 0.0,
            fact_coverage=sum(r.fact_coverage for r in results) / total if total > 0 else 0.0,
            citation_precision=(
                sum(r.citation_precision for r in results) / total if total > 0 else 0.0
            ),
            graph_path_accuracy=(
                sum(r.graph_path_accuracy for r in results) / total if total > 0 else 0.0
            ),
            mrr=sum(r.mrr for r in results) / total if total > 0 else 0.0,
            refusal_accuracy=refusal_correct_count / refusal_total if refusal_total > 0 else 1.0,
            avg_latency_ms=sum(r.latency_ms for r in results) / total if total > 0 else 0.0,
            case_results=results,
        )
