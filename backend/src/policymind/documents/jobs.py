from collections.abc import Awaitable, Callable
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from policymind.core.config import get_settings
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
        from arq import create_pool
        from arq.connections import RedisSettings

        redis = await create_pool(RedisSettings.from_dsn(self.redis_url))
        job = await redis.enqueue_job(
            "ingest_document_job", *args, _job_id=None
        )
        return job.job_id if job else "unknown"


async def ingest_document_job(
    ctx: dict[str, object],
    version_id: int,
) -> dict[str, object]:
    """ARQ 入口：从 ctx 创建 session，调用 Pipeline。"""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        pipeline = IngestionPipeline(session)
        result = await pipeline.run(version_id)
        await session.commit()
        return {"status": result.status, "stage": result.stage}
