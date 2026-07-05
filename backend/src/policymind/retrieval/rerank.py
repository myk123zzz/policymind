from collections.abc import Sequence

from policymind.retrieval.ports import SearchHit


class NoopReranker:
    """无操作重排序器：返回原顺序。用于测试和降级场景。"""

    async def rerank(
        self,
        query: str,
        candidates: Sequence[SearchHit],
        limit: int,
    ) -> list[SearchHit]:
        return list(candidates[:limit])
