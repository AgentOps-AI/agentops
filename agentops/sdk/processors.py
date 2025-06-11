"""
Span processors for AgentOps SDK.

This module contains processors for OpenTelemetry spans.
"""

from typing import Optional

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor

from agentops.logging import logger, upload_logfile


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

    def on_end(self, span: ReadableSpan) -> None:
        """
        Called when a span is ended.

        Args:
            span: The span that was ended.
        """
        # Skip if span is not sampled
        if not span.context or not span.context.trace_flags.sampled:
            return

        if self._root_span_id and (span.context.span_id is self._root_span_id):
            logger.debug(f"[agentops.InternalSpanProcessor] Ending root span: {span.name}")
            try:
                upload_logfile(span.context.trace_id)
            except Exception as e:
                logger.error(f"[agentops.InternalSpanProcessor] Error uploading logfile: {e}")

    def shutdown(self) -> None:
        """Shutdown the processor."""
        self._root_span_id = None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush the processor."""
        return True
