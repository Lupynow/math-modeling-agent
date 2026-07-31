from __future__ import annotations

from collections import Counter
from threading import Lock


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Counter[str] = Counter()

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    def render(self) -> str:
        with self._lock:
            items = sorted(self._counters.items())
        lines = [
            "# HELP modeling_agent_requests_total HTTP requests handled by endpoint.",
            "# TYPE modeling_agent_requests_total counter",
        ]
        lines.extend(f'{name} {value}' for name, value in items)
        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()
