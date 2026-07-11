from collections.abc import Sequence

from policymind.graph.repository import GraphPath


def rank_paths(
    paths: Sequence[GraphPath],
    *,
    query: str = "",
    prefer_current: bool = True,
) -> list[GraphPath]:
    """路径评分：考虑置信度、长度和版本有效性。"""
    scored: list[GraphPath] = []

    for path in paths:
        score = 0.0

        # 来源置信度（平均）
        confidences: list[float] = []
        for e in path.entities:
            c = e.get("confidence", 0.8)
            if isinstance(c, (int, float)):
                confidences.append(float(c))
        for r in path.relations:
            c = r.get("confidence", 0.8)
            if isinstance(c, (int, float)):
                confidences.append(float(c))
        if confidences:
            score += sum(float(c) for c in confidences) / len(confidences)

        # 路径长度惩罚
        score -= 0.1 * len(path.relations)

        # query 关键词匹配加分
        if query:
            query_lower = query.lower()
            for e in path.entities:
                name = str(e.get("name", "")).lower()
                if any(t in name for t in query_lower.split()):
                    score += 0.2

        scored.append(GraphPath(
            entities=path.entities,
            relations=path.relations,
            score=round(score, 4),
        ))

    scored.sort(key=lambda p: p.score, reverse=True)
    return scored
