from collections.abc import Sequence

from policymind.retrieval.ports import SearchHit


def expand_parents(
    hits: Sequence[SearchHit], *, parent_map: dict[str, str] | None = None
) -> list[SearchHit]:
    """叶子片段扩展为父级上下文。当前版本保留原命中。"""
    # Task 5 基础实现：直接返回传入的命中
    # 后续可通过 parent_map 查找父 chunk 文本
    return list(hits)
