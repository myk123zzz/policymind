"""OpenTelemetry 遥测 + Prometheus 指标暴露。"""

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


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
        self._metrics: dict[str, list[float]] = {}

    def start_span(self, name: str, **attrs: str) -> TelemetrySpan:
        return TelemetrySpan(name=name, attributes=dict(attrs))

    def record_span(self, span: TelemetrySpan) -> None:
        elapsed = span.end()
        self._spans.append({
            "name": span.name,
            "elapsed_ms": round(elapsed * 1000, 2),
            "attributes": span.attributes,
        })

    def record_metric(self, name: str, value: float) -> None:
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(value)

    def get_metrics(self) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = {}
        for name, values in self._metrics.items():
            if values:
                result[name] = {
                    "count": len(values),
                    "avg": round(sum(values) / len(values), 4),
                    "min": round(min(values), 4),
                    "max": round(max(values), 4),
                }
        return result

    def get_spans(self) -> list[dict[str, object]]:
        return self._spans


# 全局实例
telemetry = Telemetry()
