from dataclasses import dataclass, field
from typing import Literal


@dataclass(slots=True)
class DocumentBlock:
    text: str
    page_number: int
    block_type: Literal["title", "text", "table", "image", "flowchart"]
    heading_path: tuple[str, ...] = ()
    bbox: tuple[float, float, float, float] | None = None
    media_key: str | None = None


@dataclass(slots=True)
class ParsedDocument:
    title: str
    page_count: int
    blocks: list[DocumentBlock]
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class Chunk:
    id: str
    tenant_id: int
    document_id: int
    document_version_id: int
    parent_id: str | None
    level: Literal["parent", "leaf"]
    text: str
    page_number: int
    heading_path: tuple[str, ...] = ()
    bbox: tuple[float, float, float, float] | None = None
    access_level: int = 1
