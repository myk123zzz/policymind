from collections.abc import Mapping, Sequence

from policymind.retrieval.ports import SearchHit


def rrf_fuse(
    channels: Mapping[str, Sequence[SearchHit]],
    weights: Mapping[str, float] | None = None,
    *,
    k: int = 60,
    limit: int = 30,
) -> list[SearchHit]:
    """按 chunk_id 去重并融合排名，不直接比较不同渠道的原始分数。

    score(d) = Σ weight(channel) / (k + rank(channel, d))
    """
    if weights is None:
        weights = {"dense": 0.45, "bm25": 0.35, "graph": 0.20}

    scores: dict[str, float] = {}

    for channel, hits in channels.items():
        w = weights.get(channel, 0.33)
        for rank, hit in enumerate(hits, start=1):
            cid = hit.chunk_id
            scores[cid] = scores.get(cid, 0.0) + w / (k + rank)

    # 按分数降序排列
    sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)

    # 重建 SearchHit 对象
    result: list[SearchHit] = []
    id_to_hit: dict[str, SearchHit] = {}
    for hits in channels.values():
        for h in hits:
            if h.chunk_id not in id_to_hit or h.score > id_to_hit[h.chunk_id].score:
                id_to_hit[h.chunk_id] = h

    for rank, cid in enumerate(sorted_ids[:limit], start=1):
        orig = id_to_hit[cid]
        result.append(
            SearchHit(
                chunk_id=cid,
                score=round(scores[cid], 6),
                channel=orig.channel,
                rank=rank,
                text=orig.text,
            )
        )

    return result
