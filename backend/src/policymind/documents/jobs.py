from collections.abc import Awaitable, Callable
from typing import Protocol

from policymind.documents.pipeline import IngestionPipeline


class JobQueue(Protocol):
    async def enqueue(
        self, func: Callable[..., Awaitable[object]], *args: object
    ) -> str: ...


class InlineJobRunner:
    """测试用：同步执行任务，不通过 Redis。"""

    async def enqueue(
        self, func: Callable[..., Awaitable[object]], *args: object
    ) -> str:
        await func(*args)
        return "inline"


class ArqJobRunner:
    """生产用：通过 ARQ + Redis 异步执行任务。"""

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url

    async def enqueue(
        self, func: Callable[..., Awaitable[object]], *args: object
    ) -> str:
        # Task 4 占位，完整 ARQ 集成在后续补
        raise NotImplementedError("ARQ integration pending")


async def ingest_document_job(
    session_factory: object,
    version_id: int,
) -> dict[str, object]:
    """ARQ 入口：解析参数，调用 Pipeline。"""
    pipeline = IngestionPipeline(session_factory)  # type: ignore[arg-type]
    result = await pipeline.run(version_id)
    return {"status": result.status, "stage": result.stage}
