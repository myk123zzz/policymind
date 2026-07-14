#!/usr/bin/env python3
"""PolicyMind 评测脚本。

用法:
    python scripts/run_evaluation.py
    python scripts/run_evaluation.py --dataset evaluation/datasets/golden_v1.jsonl
    python scripts/run_evaluation.py --output evaluation/reports/report.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))


async def main() -> None:
    parser = argparse.ArgumentParser(description="PolicyMind Evaluation Runner")
    parser.add_argument(
        "--dataset",
        default="evaluation/datasets/golden_v1.jsonl",
        help="Path to golden dataset",
    )
    parser.add_argument(
        "--output",
        default="evaluation/reports/report.json",
        help="Path to output report",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    dataset_path = root / args.dataset
    output_path = root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    from policymind.evaluation.runner import EvaluationRunner

    print(f"Loading dataset: {dataset_path}")
    runner = EvaluationRunner(str(dataset_path))
    report = await runner.run()

    print(f"\n=== Evaluation Report ===")
    print(f"Total Cases:        {report.total_cases}")
    print(f"Routing Accuracy:   {report.routing_accuracy:.2%}")
    print(f"Fact Coverage:      {report.fact_coverage:.2%}")
    print(f"Citation Precision: {report.citation_precision:.2%}")
    print(f"Graph Path Acc:     {report.graph_path_accuracy:.2%}")
    print(f"MRR:                {report.mrr:.2%}")
    print(f"Refusal Accuracy:   {report.refusal_accuracy:.2%}")
    print(f"Avg Latency:        {report.avg_latency_ms:.0f}ms")

    # Write JSON report
    output_path.write_text(
        json.dumps(
            {
                "dataset_version": report.dataset_version,
                "total_cases": report.total_cases,
                "routing_accuracy": report.routing_accuracy,
                "fact_coverage": report.fact_coverage,
                "citation_precision": report.citation_precision,
                "graph_path_accuracy": report.graph_path_accuracy,
                "mrr": report.mrr,
                "refusal_accuracy": report.refusal_accuracy,
                "avg_latency_ms": report.avg_latency_ms,
                "case_results": [
                    {
                        "case_id": r.case_id,
                        "category": r.category,
                        "question": r.question[:60],
                        "routing_correct": r.routing_correct,
                        "fact_coverage": r.fact_coverage,
                        "refusal_correct": r.refusal_correct,
                        "latency_ms": r.latency_ms,
                        "errors": r.errors,
                    }
                    for r in report.case_results
                ],
            },
            indent=2,
        )
    )
    print(f"\nReport written to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
