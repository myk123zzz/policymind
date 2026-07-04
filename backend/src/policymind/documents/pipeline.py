import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.documents.chunking import HierarchicalChunker
from policymind.documents.models import ChunkContext
from policymind.documents.orm import DocumentVersion, IngestionJob
from policymind.documents.parsers.docx import DocxParser
from policymind.documents.parsers.markdown import MarkdownParser
from policymind.documents.parsers.pdf import PDFParser
from policymind.documents.parsers.registry import ParserRegistry
from policymind.documents.parsers.xlsx import XlsxParser
from policymind.documents.storage import LocalObjectStorage

logger = logging.getLogger(__name__)

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

# 当前 Task 4 已实现的阶段
IMPLEMENTED_STAGES = {"queued", "stored", "parsed", "chunked"}


def _build_registry() -> ParserRegistry:
    registry = ParserRegistry()
    registry.register(PDFParser())
    registry.register(DocxParser())
    registry.register(XlsxParser())
    registry.register(MarkdownParser())
    return registry


@dataclass
class IngestionResult:
    version_id: int
    stage: str
    status: str
    errors: list[str] = field(default_factory=list)


class IngestionPipeline:
    def __init__(
        self,
        session: AsyncSession,
        storage_base: str = "./data/",
    ) -> None:
        self.session = session
        self.storage_base = storage_base
        self._registry = _build_registry()
        self._chunker = HierarchicalChunker()

    async def run(self, version_id: int) -> IngestionResult:
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
        await self._get_version(version_id)
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
        if version.processing_status == stage:
            version_prev_idx = STAGE_ORDER.index(stage) - 1
            if version_prev_idx >= 0:
                return  # 已完成

        if stage == "queued":
            pass
        elif stage == "stored":
            # 验证文件在对象存储中存在
            try:
                store = LocalObjectStorage(base_path=self.storage_base)
                await store.get(version.storage_key)
            except FileNotFoundError:
                raise RuntimeError(f"File not found in storage: {version.storage_key}")
        elif stage == "parsed":
            # 真实解析文档
            content = await self._load_content(version)
            parsed = self._registry.parse(
                mime_type=version.mime_type,
                content=content,
                filename=version.storage_key,
            )
            # 暂存解析结果到版本（后续可扩展为持久化）
            version.processing_status = "parsing"
            # 解析完成
        elif stage == "chunked":
            # 真实分块
            content = await self._load_content(version)
            parsed = self._registry.parse(
                mime_type=version.mime_type,
                content=content,
                filename=version.storage_key,
            )
            context = ChunkContext(
                document_version_id=version.id,
                tenant_id=1,  # 从版本关联的文档获取
                document_id=version.document_id,
                effective_from=version.effective_from,
                effective_to=version.effective_to,
            )
            chunks = self._chunker.chunk(document=parsed, context=context)
            # chunks 产出确认（后续 Task 5 持久化到向量库）
            if not chunks:
                raise RuntimeError("Chunking produced no chunks")
        elif stage in ("embedded", "vector_indexed", "graph_indexed"):
            # Task 5/6 实现，当前跳过
            logger.info("Stage %s skipped (deferred to Task 5/6)", stage)
        elif stage == "ready":
            pass

    async def _load_content(self, version: DocumentVersion) -> bytes:
        store = LocalObjectStorage(base_path="./data/")
        return await store.get(version.storage_key)
