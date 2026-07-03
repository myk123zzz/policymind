from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.documents.orm import DocumentVersion, IngestionJob

STAGE_ORDER = [
    "queued",
    "stored",
    "parsed",
    "chunked",
    "embedded",
    "vector_indexed",
    "graph_indexed",
    "ready",
]


@dataclass
class IngestionResult:
    version_id: int
    stage: str
    status: str
    errors: list[str] = field(default_factory=list)


class IngestionPipeline:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self, version_id: int) -> IngestionResult:
        """从当前状态继续执行，已完成阶段不重复产生副作用。"""
        version = await self._get_version(version_id)
        current_stage = version.processing_status

        if current_stage not in STAGE_ORDER:
            current_stage = "queued"

        start_idx = STAGE_ORDER.index(current_stage)
        errors: list[str] = []

        for stage in STAGE_ORDER[start_idx:]:
            try:
                await self._execute_stage(stage, version)
                version.processing_status = stage
                await self.session.flush()
            except Exception as e:
                version.processing_status = stage
                version.error_message = str(e)
                await self.session.flush()
                return IngestionResult(
                    version_id=version_id,
                    stage=stage,
                    status="failed",
                    errors=errors + [str(e)],
                )

        # 更新关联的 job
        result = await self.session.execute(
            select(IngestionJob).where(
                IngestionJob.document_version_id == version_id
            )
        )
        job = result.scalar_one_or_none()
        if job:
            job.stage = "ready"
            job.status = "completed"
            await self.session.flush()

        return IngestionResult(version_id=version_id, stage="ready", status="completed")

    async def resume(self, version_id: int) -> IngestionResult:
        """从失败阶段继续执行。"""
        await self._get_version(version_id)  # validate exists
        return await self.run(version_id)

    async def _get_version(self, version_id: int) -> DocumentVersion:
        result = await self.session.execute(
            select(DocumentVersion).where(DocumentVersion.id == version_id)
        )
        version = result.scalar_one_or_none()
        if version is None:
            raise ValueError(f"DocumentVersion {version_id} not found")
        return version

    async def _execute_stage(
        self, stage: str, version: DocumentVersion
    ) -> None:
        """执行单个阶段（幂等：已完成则跳过）。"""
        if version.processing_status == stage:
            version_prev_idx = STAGE_ORDER.index(stage) - 1
            if version_prev_idx >= 0:
                # 确认前一阶段已完成
                return

        if stage == "queued":
            pass  # 初始状态
        elif stage == "stored":
            pass  # 文件已在对象存储中
        elif stage == "parsed":
            # 解析文档（使用注册的解析器）
            pass
        elif stage == "chunked":
            # 分块（使用 HierarchicalChunker）
            pass
        elif stage == "embedded":
            # 生成 embedding（Task 5 实现）
            pass
        elif stage == "vector_indexed":
            # 写入 Milvus（Task 5 实现）
            pass
        elif stage == "graph_indexed":
            # 写入 Neo4j（Task 6 实现）
            pass
        elif stage == "ready":
            pass
