from policymind.retrieval.citations import build_citations, validate_answer_citations
from policymind.retrieval.fusion import SearchHit


def make_hit(chunk_id: str, text: str = "sample text", channel: str = "dense") -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id, score=0.9, channel=channel, rank=1, text=text,
    )


def test_build_citations_from_hits() -> None:
    """从 SearchHit 构建 Citation。"""
    hits = [
        make_hit("c1", text="First citation text"),
        make_hit("c2", text="Second citation text", channel="bm25"),
    ]
    citations = build_citations(hits, document_name="policy.pdf", version="v1", page=3)
    assert len(citations) == 2
    assert citations[0].id == "c1"
    assert citations[0].document_name == "policy.pdf"
    assert citations[1].channel == "bm25"


def test_validate_detects_unknown_citation_ids() -> None:
    """检测回答中未知的引用 ID。"""
    hits = [make_hit("c1"), make_hit("c2")]
    citations = build_citations(hits, document_name="doc.pdf", version="v1", page=1)

    result = validate_answer_citations(
        answer="According to [C1] and [C3], the policy states...",
        citations=citations,
    )
    assert not result.is_valid
    assert "C3" in result.unknown_ids


def test_validate_passes_when_all_citations_known() -> None:
    """所有引用 ID 已知时验证通过。"""
    hits = [make_hit("c1"), make_hit("c2")]
    citations = build_citations(hits, document_name="doc.pdf", version="v1", page=1)

    result = validate_answer_citations(
        answer="See [C1] and [C2] for details.",
        citations=citations,
    )
    assert result.is_valid
    assert len(result.unknown_ids) == 0
