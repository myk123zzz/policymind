from collections.abc import Sequence

from policymind.retrieval.ports import SearchHit


def expand_parents(
    hits: Sequence[SearchHit],
    *,
    parent_map: dict[str, str] | None = None,
) -> list[SearchHit]:
    """叶子片段扩展为父级上下文。

    若有 parent_map，将对应 parent 文本追加到命中文本之后。
    """
    if not parent_map:
        return list(hits)

    result: list[SearchHit] = []
    for hit in hits:
        parent_text = parent_map.get(hit.chunk_id, "")
        if parent_text:
            # 保留原命中的全部元数据，仅扩展文本
            result.append(
                SearchHit(
                    chunk_id=hit.chunk_id,
                    score=hit.score,
                    channel=hit.channel,
                    rank=hit.rank,
                    text=hit.text + "\n\n" + parent_text,
                    parent_text=parent_text,
                    document_name=hit.document_name,
                    document_version=hit.document_version,
                    page_number=hit.page_number,
                    bbox=hit.bbox,
                )
            )
        else:
            result.append(hit)
    return result
