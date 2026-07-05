from policymind.retrieval.fusion import SearchHit, rrf_fuse


def hit(chunk_id: str, score: float = 0.9, channel: str = "dense") -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id, score=score, channel=channel, rank=0, text=""
    )


def test_rrf_promotes_dual_channel_hit() -> None:
    """Dense 和 BM25 都命中同一文档时，RRF 排第一。"""
    result = rrf_fuse(
        {"dense": [hit("a"), hit("b")], "bm25": [hit("b"), hit("c")]},
        k=60,
    )
    assert result[0].chunk_id == "b"


def test_rrf_deduplicates_by_chunk_id() -> None:
    """RRF 按 chunk_id 去重。"""
    result = rrf_fuse(
        {"dense": [hit("a"), hit("b")], "bm25": [hit("a"), hit("b")]},
        k=60,
    )
    ids = {h.chunk_id for h in result}
    assert ids == {"a", "b"}
    assert len(result) == 2


def test_rrf_uses_k_parameter() -> None:
    """k 参数影响分数计算。"""
    result_k60 = rrf_fuse(
        {"dense": [hit("a"), hit("b")]},
        k=60,
    )
    result_k10 = rrf_fuse(
        {"dense": [hit("a"), hit("b")]},
        k=10,
    )
    # k 值不同，分数不同
    assert result_k60[0].score != result_k10[0].score
