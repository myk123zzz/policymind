from policymind.retrieval.citations import build_citations, validate_answer_citations
from policymind.retrieval.ports import SearchHit


def make_hit(chunk_id: str, text: str = "sample text", channel: str = "dense",
             doc: str = "policy.pdf", ver: str = "v1", page: int = 3) -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id, score=0.9, channel=channel, rank=1, text=text,
        document_name=doc, document_version=ver, page_number=page,
    )


def test_build_citations_from_hits() -> None:
    hits = [
        make_hit("c1", text="First citation text"),
        make_hit("c2", text="Second citation text", channel="bm25"),
    ]
    citations = build_citations(hits)
    assert len(citations) == 2
    assert citations[0].id == "c1"
    assert citations[0].document_name == "policy.pdf"
    assert citations[1].channel == "bm25"


def test_validate_detects_unknown_citation_ids() -> None:
    hits = [make_hit("c1"), make_hit("c2")]
    citations = build_citations(hits)

    result = validate_answer_citations(
        answer="According to [C1] and [C3], the policy states...",
        citations=citations,
    )
    assert not result.is_valid
    assert "C3" in result.unknown_ids


def test_validate_passes_when_all_citations_known() -> None:
    hits = [make_hit("c1"), make_hit("c2")]
    citations = build_citations(hits)

    result = validate_answer_citations(
        answer="See [C1] and [C2] for details.",
        citations=citations,
    )
    assert result.is_valid
    assert len(result.unknown_ids) == 0
