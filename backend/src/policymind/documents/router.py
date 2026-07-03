from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.documents.orm import Document, DocumentVersion, IngestionJob
from policymind.documents.pipeline import IngestionPipeline
from policymind.infrastructure.postgres.session import get_db_session

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


class CreateDocumentRequest(BaseModel):
    logical_name: str
    category: str = "general"
    version: str = "1.0"
    content_hash: str
    storage_key: str
    mime_type: str


class DocumentJobResponse(BaseModel):
    version_id: int
    status: str
    stage: str
    error_message: str | None = None


@router.post("", response_model=DocumentJobResponse, status_code=202)
async def create_document(
    body: CreateDocumentRequest,
    session: AsyncSession = Depends(get_db_session),
) -> DocumentJobResponse:
    doc = Document(tenant_id=1, logical_name=body.logical_name, category=body.category)
    session.add(doc)
    await session.flush()

    version = DocumentVersion(
        document_id=doc.id,
        version=body.version,
        content_hash=body.content_hash,
        storage_key=body.storage_key,
        mime_type=body.mime_type,
        effective_from=datetime.utcnow(),
        processing_status="queued",
    )
    session.add(version)
    await session.flush()

    job = IngestionJob(
        tenant_id=1,
        document_version_id=version.id,
        stage="queued",
        status="pending",
    )
    session.add(job)
    await session.flush()

    # 同步执行摄取管道（测试/开发模式）
    pipeline = IngestionPipeline(session)
    result = await pipeline.run(version.id)

    return DocumentJobResponse(
        version_id=version.id,
        status=result.status,
        stage=result.stage,
    )


@router.get("")
async def list_documents(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, object]]:
    result = await session.execute(select(Document))
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "tenant_id": d.tenant_id,
            "logical_name": d.logical_name,
            "category": d.category,
            "status": d.status,
        }
        for d in docs
    ]


@router.get("/jobs/{version_id}")
async def get_job_status(
    version_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    result = await session.execute(
        select(IngestionJob).where(
            IngestionJob.document_version_id == version_id
        )
    )
    job = result.scalar_one_or_none()
    if job:
        return {"stage": job.stage, "status": job.status}
    return {"stage": "unknown", "status": "not_found"}
