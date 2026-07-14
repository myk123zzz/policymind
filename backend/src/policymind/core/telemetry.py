"""遥测收集器 + Prometheus /metrics 端点。"""

import logging
import time
from dataclasses import dataclass, field

from fastapi import APIRouter, Response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["metrics"])


@dataclass
class TelemetrySpan:
    name: str
    start_time: float = field(default_factory=time.perf_counter)
    attributes: dict[str, str] = field(default_factory=dict)

    def end(self) -> float:
        elapsed = time.perf_counter() - self.start_time
        logger.debug("Span[%s] elapsed=%.3fs attrs=%s", self.name, elapsed, self.attributes)
        return elapsed


class Telemetry:
    """内存遥测收集器，开发环境使用。"""

    def __init__(self) -> None:
        self._spans: list[dict[str, object]] = []
        self._counters: dict[str, int] = {}

    def start_span(self, name: str, **attrs: str) -> TelemetrySpan:
        return TelemetrySpan(name=name, attributes=dict(attrs))

    def record_span(self, span: TelemetrySpan) -> None:
        elapsed = span.end()
        self._spans.append({
            "name": span.name,
            "elapsed_ms": round(elapsed * 1000, 2),
            "attributes": span.attributes,
        })

    def increment(self, name: str) -> None:
        self._counters[name] = self._counters.get(name, 0) + 1

    def get_metrics_text(self) -> str:
        """生成 Prometheus text format。"""
        lines: list[str] = []
        for name, val in self._counters.items():
            safe_name = name.replace("-", "_").replace(" ", "_")
            lines.append(f"# HELP {safe_name} PolicyMind metric")
            lines.append(f"# TYPE {safe_name} counter")
            lines.append(f"{safe_name} {val}")
        lines.append(f"spans_total {len(self._spans)}")
        return "\n".join(lines) + "\n"


# 全局实例
telemetry = Telemetry()


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    """Prometheus /metrics 端点。"""
    return Response(
        content=telemetry.get_metrics_text(),
        media_type="text/plain; version=0.0.4",
    )
