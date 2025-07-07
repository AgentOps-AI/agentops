from __future__ import annotations

"""Collect and provide per-trace span statistics for AgentOps SDK.

This lightweight utility gathers metrics as spans are ended via the
InternalSpanProcessor so that we can show useful summary information at the
end of a session (root span).
"""

from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, Optional, Union

from opentelemetry.sdk.trace import ReadableSpan, Span

from agentops.semconv.span_attributes import SpanAttributes

__all__ = [
    "TraceStats",
    "record_span",
    "get_trace_stats",
]


@dataclass
class TraceStats:
    """Container for statistics about a single trace (session)."""

    total_spans: int = 0
    tools: int = 0
    llms: int = 0
    total_cost: float = 0.0

    def update(self, span: Union[ReadableSpan, Span]) -> None:
        """Update counters using attributes from the provided span."""
        self.total_spans += 1

        # Span kind classification (case-insensitive)
        span_kind: Optional[str] = None
        try:
            span_kind = span.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND)  # type: ignore[attr-defined]
        except Exception:
            # In case attributes is None or not dict-like
            span_kind = None

        if isinstance(span_kind, str):
            kind = span_kind.lower()
            if "tool" in kind:
                self.tools += 1
            if "llm" in kind:
                self.llms += 1

        # Cost aggregation – cost may come from tools or LLM spans.
        cost_attr = SpanAttributes.LLM_USAGE_TOOL_COST
        try:
            cost_val: Any = span.attributes.get(cost_attr)  # type: ignore[attr-defined]
        except Exception:
            cost_val = None
        if cost_val is not None:
            try:
                self.total_cost += float(cost_val)
            except (TypeError, ValueError):
                # Ignore non-numeric cost values
                pass


# Internal storage for stats keyed by trace_id (int)
_STATS: Dict[int, TraceStats] = {}
_STATS_LOCK: Lock = Lock()


def record_span(span: Union[ReadableSpan, Span]) -> None:
    """Record a finished span into the statistics registry."""
    try:
        trace_id: int = span.context.trace_id  # type: ignore[attr-defined]
    except Exception:
        return  # Cannot extract trace ID – ignore

    with _STATS_LOCK:
        stats = _STATS.setdefault(trace_id, TraceStats())
        stats.update(span)


def get_trace_stats(trace_id: Union[int, str]) -> Optional[TraceStats]:
    """Return the statistics object for *trace_id* if it exists."""
    if isinstance(trace_id, str):
        try:
            trace_id = int(trace_id, 16)  # Convert hex string to int
        except ValueError:
            # Fallback – attempt decimal conversion or ignore
            try:
                trace_id = int(trace_id)
            except ValueError:
                return None

    with _STATS_LOCK:
        return _STATS.get(trace_id)