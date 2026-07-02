import tempfile

import pytest


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_local_storage_put_and_get(temp_dir: str) -> None:
    """本地存储写入和读取。"""
    from policymind.documents.storage import LocalObjectStorage

    storage = LocalObjectStorage(base_path=temp_dir)
    content = b"hello world"
    storage.put(key="doc/1/test.txt", content=content, content_type="text/plain")

    result = storage.get(key="doc/1/test.txt")
    assert result == content


def test_local_storage_delete(temp_dir: str) -> None:
    """本地存储删除。"""
    from policymind.documents.storage import LocalObjectStorage

    storage = LocalObjectStorage(base_path=temp_dir)
    storage.put(key="doc/1/to-delete.txt", content=b"data", content_type="text/plain")
    storage.delete(key="doc/1/to-delete.txt")

    with pytest.raises(FileNotFoundError):
        storage.get(key="doc/1/to-delete.txt")


def test_local_storage_key_security(temp_dir: str) -> None:
    """本地存储 Key 可包含路径分隔符，不会创建意外目录结构。"""
    from policymind.documents.storage import LocalObjectStorage

    storage = LocalObjectStorage(base_path=temp_dir)

    # Keys with path-like segments should work
    safe_key = "1/a1b2c3/file.pdf"
    storage.put(key=safe_key, content=b"test", content_type="application/pdf")
    result = storage.get(key=safe_key)
    assert result == b"test"
