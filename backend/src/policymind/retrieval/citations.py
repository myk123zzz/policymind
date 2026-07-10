import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from policymind.retrieval.ports import SearchHit


@dataclass(slots=True)
class Citation:
    id: str
    document_name: str = ""
    document_version: str = ""
    page_number: int = 1
    quote: str = ""
    bbox: tuple[float, float, float, float] | None = None
    channel: str = ""
    score: float = 0.0


@dataclass(slots=True)
class CitationValidation:
    is_valid: bool
    unknown_ids: set[str] = field(default_factory=set)
    missing_ids: set[str] = field(default_factory=set)


def build_citations(
    hits: Sequence[SearchHit],
) -> list[Citation]:
    """将 SearchHit 列表转换为 Citation 列表，使用命中自带的元数据。"""
    citations: list[Citation] = []
    for hit in hits:
        citations.append(
            Citation(
                id=hit.chunk_id,
                document_name=hit.document_name,
                document_version=hit.document_version,
                page_number=hit.page_number,
                quote=hit.text[:200],
                bbox=hit.bbox,
                channel=hit.channel,
                score=hit.score,
            )
        )
    return citations


def validate_answer_citations(
    answer: str,
    citations: Sequence[Citation],
) -> CitationValidation:
    """找出答案中缺失、未知和未使用的 Citation ID。"""
    valid_ids = {c.id.upper() for c in citations}
    raw_refs = set(re.findall(r"\[([Cc]\d+)\]", answer))
    referenced = {r.upper() for r in raw_refs}
    unknown = referenced - valid_ids
    missing = valid_ids - referenced if valid_ids else set()
    return CitationValidation(
        is_valid=len(unknown) == 0,
        unknown_ids=unknown,
        missing_ids=missing,
    )
