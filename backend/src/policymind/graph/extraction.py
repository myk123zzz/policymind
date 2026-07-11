import json
import logging
import re
from dataclasses import dataclass, field

from policymind.graph.ontology import is_valid_entity, is_valid_relation

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GraphExtraction:
    entities: list[dict[str, object]] = field(default_factory=list)
    relations: list[dict[str, object]] = field(default_factory=list)


def extract_json_object(text: str) -> dict[str, object]:
    """优先 JSON 代码块，再以平衡括号扫描提取首个完整对象。"""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    if start == -1:
        return {}

    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])  # type: ignore[no-any-return]
                except json.JSONDecodeError:
                    return {}
    return {}


def validate_extraction(
    raw: dict[str, object],
    source_chunk_id: str,
    tenant_id: int,
    document_version_id: int,
) -> GraphExtraction:
    """校验并清洗抽取结果，拒绝无效实体/关系。"""
    entities: list[dict[str, object]] = []
    relations: list[dict[str, object]] = []

    for e in raw.get("entities", []):  # type: ignore[attr-defined]
        if not isinstance(e, dict):
            continue
        etype = str(e.get("type", ""))
        if not is_valid_entity(etype):
            continue
        eid = str(e.get("id", ""))
        if not eid:
            continue
        entities.append({
            "id": eid,
            "type": etype,
            "name": str(e.get("name", eid)),
            "tenant_id": tenant_id,
            "source_document_version_id": document_version_id,
            "source_chunk_id": source_chunk_id,
            "confidence": float(e.get("confidence", 0.8)),
        })

    entity_ids = {e["id"] for e in entities}
    for r in raw.get("relations", []):  # type: ignore[attr-defined]
        if not isinstance(r, dict):
            continue
        rtype = str(r.get("type", ""))
        if not is_valid_relation(rtype):
            continue
        src = str(r.get("source", ""))
        tgt = str(r.get("target", ""))
        if src not in entity_ids or tgt not in entity_ids:
            continue  # 端点不存在则拒绝
        relations.append({
            "source": src,
            "target": tgt,
            "type": rtype,
            "tenant_id": tenant_id,
            "source_document_version_id": document_version_id,
            "source_chunk_id": source_chunk_id,
            "confidence": float(r.get("confidence", 0.8)),
        })

    return GraphExtraction(entities=entities, relations=relations)


class GraphExtractor:
    """图谱抽取器：从 Chunk 文本抽取结构化实体和关系。"""

    async def extract(
        self,
        chunk_text: str,
        chunk_id: str,
        tenant_id: int,
        document_version_id: int,
    ) -> GraphExtraction:
        """抽取并校验实体关系，拒绝无来源或端点不存在的无效数据。"""
        # 从 chunk 文本中提取 JSON
        raw = extract_json_object(chunk_text)
        if not raw:
            return GraphExtraction()

        # 校验 + 白名单过滤
        return validate_extraction(
            raw=raw,
            source_chunk_id=chunk_id,
            tenant_id=tenant_id,
            document_version_id=document_version_id,
        )
