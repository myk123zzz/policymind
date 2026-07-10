from policymind.retrieval.parent_expansion import expand_parents
from policymind.retrieval.ports import SearchHit


def test_expand_parents_appends_parent_text() -> None:
    hits = [
        SearchHit(chunk_id="c1", score=0.9, channel="dense", rank=1, text="leaf"),
        SearchHit(chunk_id="c2", score=0.8, channel="bm25", rank=2, text="leaf2"),
    ]
    parent_map = {"c1": "parent for c1"}

    result = expand_parents(hits, parent_map=parent_map)
    assert "parent for c1" in result[0].text
    assert result[0].text.startswith("leaf")


def test_expand_parents_noop_without_map() -> None:
    hits = [SearchHit(chunk_id="c1", score=0.9, channel="dense", rank=1, text="leaf")]
    result = expand_parents(hits)
    assert result[0].text == "leaf"


def test_expand_parents_preserves_metadata() -> None:
    """Parent expansion 后保留 document_name/version/page/bbox 元数据。"""
    hits = [
        SearchHit(
            chunk_id="c1", score=0.9, channel="dense", rank=1,
            text="leaf text",
            document_name="policy.pdf", document_version="v2",
            page_number=5, bbox=(10.0, 20.0, 100.0, 200.0),
        )
    ]
    parent_map = {"c1": "parent context"}

    result = expand_parents(hits, parent_map=parent_map)
    hit = result[0]
    assert "parent context" in hit.text
    assert hit.document_name == "policy.pdf"
    assert hit.document_version == "v2"
    assert hit.page_number == 5
    assert hit.bbox == (10.0, 20.0, 100.0, 200.0)
