import hashlib
from collections.abc import Sequence


class MemoryEmbeddingProvider:
    """测试用：基于文本哈希生成确定性向量。"""

    dimension: int = 128
    model_name: str = "memory-deterministic"

    def __init__(self, dimension: int = 128) -> None:
        self.dimension = dimension

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode()).digest()
        result: list[float] = []
        for i in range(self.dimension):
            b = h[i % len(h)]
            result.append((b / 255.0) * 2.0 - 1.0)
        return result
