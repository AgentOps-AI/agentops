"""
Span processors for AgentOps SDK.

This module contains processors for OpenTelemetry spans.
"""

from typing import Optional, Dict, Any

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor

from agentops.logging import logger, upload_logfile
from agentops.semconv import SpanAttributes, SpanKind


class InternalSpanProcessor(SpanProcessor):
    """
    A span processor that prints information about spans.

    This processor is particularly useful for debugging and monitoring
    as it prints information about spans as they are created and ended.
    For session spans, it prints a URL to the AgentOps dashboard.

    Note about span kinds:
    - OpenTelemetry spans have a native 'kind' property (INTERNAL, CLIENT, CONSUMER, etc.)
    - AgentOps also uses a semantic convention attribute AGENTOPS_SPAN_KIND for domain-specific kinds
    - This processor tries to use the native kind first, then falls back to the attribute
    """

    _root_span_id: Optional[int] = None
    _trace_statistics: Dict[int, Dict[str, Any]] = {}  # Map trace_id to statistics

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        """
        Called when a span is started.

        Args:
            span: The span that was started.
            parent_context: The parent context, if any.
        """
        # Skip if span is not sampled
        if not span.context or not span.context.trace_flags.sampled:
            return

        if not self._root_span_id:
            self._root_span_id = span.context.span_id
            logger.debug(f"[agentops.InternalSpanProcessor] Found root span: {span.name}")
            
            # Initialize statistics for this trace
            trace_id = span.context.trace_id
            if trace_id not in self._trace_statistics:
                self._trace_statistics[trace_id] = {
                    "total_spans": 0,
                    "tool_count": 0,
                    "llm_count": 0,
                    "total_cost": 0.0
                }

    def on_end(self, span: ReadableSpan) -> None:
        """
        Called when a span is ended.

        Args:
            span: The span that was ended.
        """
        # Skip if span is not sampled
        if not span.context or not span.context.trace_flags.sampled:
            return

        # Collect statistics for the trace
        trace_id = span.context.trace_id
        if trace_id in self._trace_statistics:
            stats = self._trace_statistics[trace_id]
            
            # Increment total span count
            stats["total_spans"] += 1
            
            # Check span kind for tools and LLM calls
            span_kind = span.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND, "") if span.attributes else ""
            
            if span_kind == SpanKind.TOOL:
                stats["tool_count"] += 1
            elif span_kind == SpanKind.LLM:
                stats["llm_count"] += 1
            
            # Accumulate cost from LLM calls and tools
            if span.attributes:
                cost = span.attributes.get(SpanAttributes.LLM_USAGE_TOOL_COST, 0.0)
                if cost:
                    stats["total_cost"] += float(cost)

        if self._root_span_id and (span.context.span_id is self._root_span_id):
            logger.debug(f"[agentops.InternalSpanProcessor] Ending root span: {span.name}")
            try:
                upload_logfile(span.context.trace_id)
            except Exception as e:
                logger.error(f"[agentops.InternalSpanProcessor] Error uploading logfile: {e}")

    def get_trace_statistics(self, trace_id: int) -> Dict[str, Any]:
        """
        Get the collected statistics for a specific trace.
        
        Args:
            trace_id: The trace ID to get statistics for.
            
        Returns:
            Dictionary containing trace statistics or empty dict if not found.
        """
        return self._trace_statistics.get(trace_id, {
            "total_spans": 0,
            "tool_count": 0,
            "llm_count": 0,
            "total_cost": 0.0
        })

    def shutdown(self) -> None:
        """Shutdown the processor."""
        self._root_span_id = None
        self._trace_statistics.clear()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush the processor."""
        return True
