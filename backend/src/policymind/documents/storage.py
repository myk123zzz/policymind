import asyncio
from pathlib import Path
from typing import Protocol


class ObjectStorage(Protocol):
    async def put(self, key: str, content: bytes, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...


class LocalObjectStorage:
    def __init__(self, base_path: str) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        for part in Path(key).parts:
            if part in ("..", "/", "\\"):
                raise ValueError(f"Invalid key component: {part!r}")
        return self.base_path / key

    async def put(self, key: str, content: bytes, content_type: str) -> None:
        fp = self._full_path(key)
        fp.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(fp.write_bytes, content)

    async def get(self, key: str) -> bytes:
        fp = self._full_path(key)
        if not fp.exists():
            raise FileNotFoundError(f"Object not found: {key}")
        return await asyncio.to_thread(fp.read_bytes)

    async def delete(self, key: str) -> None:
        fp = self._full_path(key)
        if fp.exists():
            await asyncio.to_thread(fp.unlink)
            for parent in fp.parents:
                if parent == self.base_path:
                    break
                try:
                    await asyncio.to_thread(parent.rmdir)
                except OSError:
                    break


class S3ObjectStorage:
    """S3/MinIO 对象存储（Task 4+ 完整实现）。"""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
    ) -> None:
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket

    async def put(self, key: str, content: bytes, content_type: str) -> None:
        raise NotImplementedError("S3 storage will be implemented in Task 4")

    async def get(self, key: str) -> bytes:
        raise NotImplementedError("S3 storage will be implemented in Task 4")

    async def delete(self, key: str) -> None:
        raise NotImplementedError("S3 storage will be implemented in Task 4")
