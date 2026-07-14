from policymind.evaluation.metrics import (
    citation_precision,
    graph_path_accuracy,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
    required_fact_coverage,
)


def test_recall_at_k_all_found() -> None:
    assert recall_at_k(["a", "b", "c"], {"a", "b"}, k=3) == 1.0


def test_recall_at_k_partial() -> None:
    assert recall_at_k(["a", "c"], {"a", "b"}, k=2) == 0.5


def test_recall_empty_relevant() -> None:
    assert recall_at_k(["a", "b"], set(), k=2) == 1.0


def test_reciprocal_rank_first_position() -> None:
    assert reciprocal_rank(["a", "b", "c"], {"a"}) == 1.0


def test_reciprocal_rank_not_found() -> None:
    assert reciprocal_rank(["a", "b"], {"c"}) == 0.0


def test_ndcg_at_k() -> None:
    result = ndcg_at_k(["a", "b", "c"], {"a": 3.0, "b": 2.0, "c": 1.0}, k=3)
    assert result > 0.0


def test_citation_precision_perfect() -> None:
    assert citation_precision({"C1", "C2"}, {"C1", "C2"}) == 1.0


def test_citation_precision_extra() -> None:
    assert citation_precision({"C1", "C2", "C3"}, {"C1", "C2"}) == 2 / 3


def test_graph_path_accuracy() -> None:
    assert graph_path_accuracy(["e1", "e2"], ["e1", "e2"]) == 1.0
    assert graph_path_accuracy(["e1"], ["e1", "e2"]) == 0.5


def test_required_fact_coverage_all_matched() -> None:
    result = required_fact_coverage(
        "The procurement policy requires manager approval for amounts over $5,000.",
        ["manager approval", "$5,000"],
    )
    assert result == 1.0


def test_required_fact_coverage_partial() -> None:
    result = required_fact_coverage(
        "The policy requires manager approval.",
        ["manager approval", "CFO approval"],
    )
    assert result == 0.5


def test_required_fact_coverage_empty_facts() -> None:
    result = required_fact_coverage("Some answer", [])
    assert result == 1.0
