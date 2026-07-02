import pytest


def test_rejects_extension_mime_mismatch() -> None:
    """扩展名与 MIME 类型不一致时拒绝上传。"""
    from policymind.documents.validation import validate_upload

    with pytest.raises(ValueError, match="MIME"):
        validate_upload(
            filename="report.pdf",
            declared_mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content=b"valid content",
            max_bytes=10 * 1024 * 1024,
        )


def test_rejects_empty_file() -> None:
    """拒绝空文件。"""
    from policymind.documents.validation import validate_upload

    with pytest.raises(ValueError, match="empty"):
        validate_upload(
            filename="empty.pdf",
            declared_mime="application/pdf",
            content=b"",
            max_bytes=10 * 1024 * 1024,
        )


def test_rejects_exceeds_max_size() -> None:
    """拒绝超过限制大小的文件。"""
    from policymind.documents.validation import validate_upload

    with pytest.raises(ValueError, match="size"):
        validate_upload(
            filename="large.pdf",
            declared_mime="application/pdf",
            content=b"x" * 1024,
            max_bytes=512,
        )


def test_accepts_valid_pdf() -> None:
    """接受有效的 PDF 文件。"""
    from policymind.documents.validation import validate_upload

    # Minimal valid PDF: header + trailer
    minimal_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n110\n%%EOF"
    )
    result = validate_upload(
        filename="test.pdf",
        declared_mime="application/pdf",
        content=minimal_pdf,
        max_bytes=10 * 1024 * 1024,
    )
    assert result.mime_type == "application/pdf"


def test_accepts_valid_markdown() -> None:
    """接受 Markdown 文件。"""
    from policymind.documents.validation import validate_upload

    result = validate_upload(
        filename="readme.md",
        declared_mime="text/markdown",
        content=b"# Hello\n\nThis is markdown.",
        max_bytes=10 * 1024 * 1024,
    )
    assert result.mime_type == "text/markdown"


def test_safe_storage_key_is_random() -> None:
    """存储 Key 为随机生成，不包含原始文件名。"""
    from policymind.documents.validation import safe_storage_key

    key = safe_storage_key(tenant_id=1, suffix=".pdf")
    assert "/" in key
    assert ".pdf" not in key.split("/")[-1] or key.endswith(".pdf")
    # Key should be different each time
    key2 = safe_storage_key(tenant_id=1, suffix=".pdf")
    assert key != key2
