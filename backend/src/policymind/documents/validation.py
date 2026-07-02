import uuid
from dataclasses import dataclass
from pathlib import Path

import filetype  # type: ignore[import-untyped]

MIME_TO_EXTENSIONS: dict[str, set[str]] = {
    "application/pdf": {".pdf"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {".xlsx"},
    "text/markdown": {".md", ".markdown"},
    "text/plain": {".txt"},
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
}

EXTENSION_TO_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


@dataclass(slots=True)
class ValidatedUpload:
    filename: str
    mime_type: str
    content: bytes
    size_bytes: int


def validate_upload(
    filename: str,
    declared_mime: str,
    content: bytes,
    max_bytes: int,
) -> ValidatedUpload:
    """同时验证扩展名、MIME、文件魔数、大小和空文件。"""
    ext = Path(filename).suffix.lower()

    # 检查空文件
    if len(content) == 0:
        raise ValueError("File is empty")

    # 检查大小
    if len(content) > max_bytes:
        raise ValueError(f"File size {len(content)} exceeds max {max_bytes} bytes")

    # 检查扩展名
    if ext not in EXTENSION_TO_MIME:
        raise ValueError(f"Unsupported file extension: {ext}")

    # 检查 MIME
    expected_mime = EXTENSION_TO_MIME[ext]

    # Markdown 和纯文本需要宽松检查 (无魔数)
    if ext in {".md", ".markdown", ".txt"}:
        if declared_mime not in ("text/markdown", "text/plain"):
            raise ValueError(
                f"MIME type {declared_mime} does not match extension {ext}"
            )
        return ValidatedUpload(
            filename=filename,
            mime_type=expected_mime,
            content=content,
            size_bytes=len(content),
        )

    if declared_mime != expected_mime:
        raise ValueError(f"MIME type {declared_mime} mismatch for extension {ext}")

    # 检查文件魔数
    kind = filetype.guess(content)
    if kind is None:
        # 宽松处理：某些合法文件 filetype 可能无法识别
        pass
    elif kind.mime != expected_mime:
        raise ValueError(
            f"File magic number mismatch: detected {kind.mime}, expected {expected_mime}"
        )

    return ValidatedUpload(
        filename=filename,
        mime_type=expected_mime,
        content=content,
        size_bytes=len(content),
    )


def safe_storage_key(tenant_id: int, suffix: str) -> str:
    """生成 tenant/uuid 形式的对象 Key，不拼接原始文件名。"""
    return f"{tenant_id}/{uuid.uuid4().hex}{suffix}"
