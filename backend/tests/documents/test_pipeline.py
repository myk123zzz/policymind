from datetime import UTC, datetime

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def sample_doc(db_session: AsyncSession, tmp_path) -> int:
    from policymind.documents.orm import Document, DocumentVersion

    doc = Document(tenant_id=1, logical_name="test-policy", category="general")
    db_session.add(doc)
    await db_session.flush()

    version = DocumentVersion(
        document_id=doc.id,
        version="1.0",
        content_hash="abc123",
        storage_key="done",
        mime_type="text/markdown",
        effective_from=datetime.now(UTC),
        processing_status="chunked",
    )
    db_session.add(version)
    await db_session.flush()
    return version.id


async def test_pipeline_completes(
    db_session: AsyncSession, sample_doc: int
) -> None:
    from policymind.documents.pipeline import IngestionPipeline
    from policymind.documents.storage import LocalObjectStorage

    storage = LocalObjectStorage(base_path="./data/")
    pipeline = IngestionPipeline(db_session, storage=storage)
    result = await pipeline.run(sample_doc)

    assert result.stage == "ready"
    assert result.status == "completed"


async def test_pipeline_resume(
    db_session: AsyncSession, sample_doc: int
) -> None:
    from policymind.documents.orm import DocumentVersion
    from policymind.documents.pipeline import IngestionPipeline
    from policymind.documents.storage import LocalObjectStorage

    result = await db_session.execute(
        select(DocumentVersion).where(DocumentVersion.id == sample_doc)
    )
    version = result.scalar_one()
    version.processing_status = "embedded"
    await db_session.flush()

    storage = LocalObjectStorage(base_path="./data/")
    pipeline = IngestionPipeline(db_session, storage=storage)
    result = await pipeline.run(sample_doc)

    assert result.stage == "ready"


async def test_job_tracked(
    db_session: AsyncSession, sample_doc: int
) -> None:
    from policymind.documents.pipeline import IngestionJob, IngestionPipeline
    from policymind.documents.storage import LocalObjectStorage

    job = IngestionJob(
        tenant_id=1,
        document_version_id=sample_doc,
        stage="queued",
        status="pending",
    )
    db_session.add(job)
    await db_session.flush()

    storage = LocalObjectStorage(base_path="./data/")
    pipeline = IngestionPipeline(db_session, storage=storage)
    await pipeline.run(sample_doc)

    await db_session.refresh(job)
    assert job.status == "completed"
    assert job.stage == "ready"
