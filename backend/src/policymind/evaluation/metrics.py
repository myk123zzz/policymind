"""评测指标：Recall@K, MRR, NDCG, Citation Precision, Graph Path Accuracy, Fact Coverage。"""

from collections.abc import Mapping, Sequence


def recall_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 1.0
    top_k = set(retrieved[:k])
    return len(top_k & relevant) / len(relevant)


def reciprocal_rank(retrieved: Sequence[str], relevant: set[str]) -> float:
    for i, doc_id in enumerate(retrieved, 1):
        if doc_id in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(
    retrieved: Sequence[str], gains: Mapping[str, float], k: int
) -> float:
    import math

    dcg = 0.0
    for i, doc_id in enumerate(retrieved[:k], 1):
        gain = gains.get(doc_id, 0.0)
        dcg += gain / math.log2(i + 1)

    ideal_gains = sorted(gains.values(), reverse=True)
    idcg = 0.0
    for i in range(min(k, len(ideal_gains))):
        idcg += ideal_gains[i] / math.log2(i + 2)

    return dcg / idcg if idcg > 0 else 0.0


def citation_precision(answer_ids: set[str], valid_ids: set[str]) -> float:
    if not answer_ids:
        return 1.0 if not valid_ids else 0.0
    return len(answer_ids & valid_ids) / len(answer_ids)


def graph_path_accuracy(actual: Sequence[str], expected: Sequence[str]) -> float:
    if not expected:
        return 1.0 if not actual else 0.0
    actual_set = set(actual)
    expected_set = set(expected)
    return len(actual_set & expected_set) / len(expected_set)


def required_fact_coverage(answer: str, facts: Sequence[str]) -> float:
    if not facts:
        return 1.0
    answer_lower = answer.lower()
    matched = sum(1 for f in facts if f.lower() in answer_lower)
    return matched / len(facts)
