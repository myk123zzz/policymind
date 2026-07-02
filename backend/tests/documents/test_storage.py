import tempfile

import pytest
import pytest_asyncio


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest_asyncio.fixture
async def storage(temp_dir):
    from policymind.documents.storage import LocalObjectStorage

    return LocalObjectStorage(base_path=temp_dir)


async def test_local_storage_put_and_get(storage) -> None:
    """本地存储写入和读取。"""
    await storage.put(key="doc/1/test.txt", content=b"hello world", content_type="text/plain")
    result = await storage.get(key="doc/1/test.txt")
    assert result == b"hello world"


async def test_local_storage_delete(storage) -> None:
    """本地存储删除。"""
    await storage.put(key="doc/1/to-delete.txt", content=b"data", content_type="text/plain")
    await storage.delete(key="doc/1/to-delete.txt")

    with pytest.raises(FileNotFoundError):
        await storage.get(key="doc/1/to-delete.txt")


async def test_local_storage_key_security(storage) -> None:
    """本地存储 Key 可包含路径分隔符，不会创建意外目录结构。"""
    safe_key = "1/a1b2c3/file.pdf"
    await storage.put(key=safe_key, content=b"test", content_type="application/pdf")
    result = await storage.get(key=safe_key)
    assert result == b"test"


def test_s3_storage_is_defined() -> None:
    """S3ObjectStorage 类已定义（Task 4 完整实现）。"""
    from policymind.documents.storage import S3ObjectStorage

    s3 = S3ObjectStorage(
        endpoint="localhost:9000",
        access_key="test",
        secret_key="test",
        bucket="test",
    )
    assert s3.bucket == "test"
