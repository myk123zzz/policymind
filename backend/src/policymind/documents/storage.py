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
        # 防止路径遍历攻击
        for part in Path(key).parts:
            if part in ("..", "/", "\\"):
                raise ValueError(f"Invalid key component: {part!r}")
        return self.base_path / key

    def put(self, key: str, content: bytes, content_type: str) -> None:
        fp = self._full_path(key)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_bytes(content)

    def get(self, key: str) -> bytes:
        fp = self._full_path(key)
        if not fp.exists():
            raise FileNotFoundError(f"Object not found: {key}")
        return fp.read_bytes()

    def delete(self, key: str) -> None:
        fp = self._full_path(key)
        if fp.exists():
            fp.unlink()
            # 清理空父目录
            for parent in fp.parents:
                if parent == self.base_path:
                    break
                try:
                    parent.rmdir()
                except OSError:
                    break
