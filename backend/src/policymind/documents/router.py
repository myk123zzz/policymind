from datetime import UTC, datetime

from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.auth.dependencies import RequestContext, get_current_context
from policymind.documents.orm import Document, DocumentVersion, IngestionJob
from policymind.documents.pipeline import IngestionPipeline
from policymind.documents.validation import safe_storage_key, validate_upload
from policymind.infrastructure.postgres.session import get_db_session

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


class DocumentJobResponse(BaseModel):
    version_id: int
    status: str
    stage: str
    error_message: str | None = None


@router.post("", response_model=DocumentJobResponse, status_code=202)
async def create_document(
    file: UploadFile,
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentJobResponse:
    content = await file.read()
    filename = file.filename or "upload"

    # 校验并确定 MIME
    validated = validate_upload(
        filename=filename,
        declared_mime=file.content_type or "application/octet-stream",
        content=content,
        max_bytes=50 * 1024 * 1024,
    )

    # 生成安全存储 Key 并写入存储
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    storage_key = safe_storage_key(ctx.tenant_id, suffix=f".{ext}")
    from policymind.documents.storage import LocalObjectStorage

    storage = LocalObjectStorage(base_path="./data/")
    await storage.put(key=storage_key, content=validated.content, content_type=validated.mime_type)

    # 计算内容哈希
    import hashlib
    content_hash = hashlib.sha256(validated.content).hexdigest()

    # 创建文档记录
    doc = Document(
        tenant_id=ctx.tenant_id,
        logical_name=filename,
        category="general",
    )
    session.add(doc)
    await session.flush()

    version = DocumentVersion(
        document_id=doc.id,
        version="1.0",
        content_hash=content_hash,
        storage_key=storage_key,
        mime_type=validated.mime_type,
        effective_from=datetime.now(UTC),
        processing_status="queued",
    )
    session.add(version)
    await session.flush()

    job = IngestionJob(
        tenant_id=ctx.tenant_id,
        document_version_id=version.id,
        stage="queued",
        status="pending",
    )
    session.add(job)
    await session.flush()

    # 同步执行摄取管道
    pipeline = IngestionPipeline(session)
    result = await pipeline.run(version.id)

    return DocumentJobResponse(
        version_id=version.id,
        status=result.status,
        stage=result.stage,
    )


@router.get("")
async def list_documents(
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, object]]:
    result = await session.execute(
        select(Document).where(Document.tenant_id == ctx.tenant_id)
    )
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
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    result = await session.execute(
        select(IngestionJob).where(
            IngestionJob.document_version_id == version_id,
            IngestionJob.tenant_id == ctx.tenant_id,
        )
    )
    job = result.scalar_one_or_none()
    if job:
        return {"stage": job.stage, "status": job.status}
    return {"stage": "unknown", "status": "not_found"}
