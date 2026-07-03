import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def sample_doc(db_session: AsyncSession) -> int:
    """创建一个文档版本记录，返回 version_id。"""
    from datetime import datetime

    from policymind.documents.orm import Document, DocumentVersion

    doc = Document(tenant_id=1, logical_name="test-policy", category="general")
    db_session.add(doc)
    await db_session.flush()

    version = DocumentVersion(
        document_id=doc.id,
        version="1.0",
        content_hash="abc123",
        storage_key="1/test.pdf",
        mime_type="text/markdown",
        effective_from=datetime.utcnow(),
        processing_status="queued",
    )
    db_session.add(version)
    await db_session.flush()
    return version.id


async def test_pipeline_stages_progress(
    db_session: AsyncSession, sample_doc: int
) -> None:
    """摄取管道按顺序推进阶段状态。"""
    from policymind.documents.pipeline import IngestionPipeline

    pipeline = IngestionPipeline(db_session)
    result = await pipeline.run(sample_doc)

    assert result.stage == "ready"
    assert result.status == "completed"


async def test_pipeline_idempotent_resume(
    db_session: AsyncSession, sample_doc: int
) -> None:
    """管道可从中断阶段恢复。"""
    from policymind.documents.orm import DocumentVersion
    from policymind.documents.pipeline import IngestionPipeline

    # 标记为部分完成
    result = await db_session.execute(
        select(DocumentVersion).where(DocumentVersion.id == sample_doc)
    )
    version = result.scalar_one()
    version.processing_status = "parsed"
    await db_session.flush()

    pipeline = IngestionPipeline(db_session)
    result = await pipeline.run(sample_doc)

    # 应该从 parsed 之后的阶段继续
    assert result.stage == "ready"


async def test_ingestion_job_status_tracked(
    db_session: AsyncSession, sample_doc: int
) -> None:
    """任务状态可在 IngestionJob 中追踪。"""

    from policymind.documents.pipeline import IngestionJob, IngestionPipeline

    job = IngestionJob(
        tenant_id=1,
        document_version_id=sample_doc,
        stage="queued",
        status="pending",
    )
    db_session.add(job)
    await db_session.flush()

    pipeline = IngestionPipeline(db_session)
    await pipeline.run(sample_doc)

    # 刷新 job 状态
    await db_session.refresh(job)
    assert job.status == "completed"
    assert job.stage == "ready"
