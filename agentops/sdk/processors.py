"""
Span processors for AgentOps SDK.

This module contains processors for OpenTelemetry spans.
"""

import time
from threading import Event, Lock, Thread
from typing import Dict, Optional

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter

from agentops.logging import logger
from agentops.helpers.dashboard import log_trace_url
from agentops.semconv.core import CoreAttributes
from agentops.logging import upload_logfile


class LiveSpanProcessor(SpanProcessor):
    def __init__(self, span_exporter: SpanExporter, **kwargs):
        self.span_exporter = span_exporter
        self._in_flight: Dict[int, Span] = {}
        self._lock = Lock()
        self._stop_event = Event()
        self._export_thread = Thread(target=self._export_periodically, daemon=True)
        self._export_thread.start()

    def _export_periodically(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(1)
            with self._lock:
                to_export = [self._readable_span(span) for span in self._in_flight.values()]
                if to_export:
                    self.span_exporter.export(to_export)

    def _readable_span(self, span: Span) -> ReadableSpan:
        readable = span._readable_span()
        readable._end_time = time.time_ns()
        readable._attributes = {
            **(readable._attributes or {}),
            CoreAttributes.IN_FLIGHT: True,
        }
        return readable

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        if not span.context or not span.context.trace_flags.sampled:
            return
        with self._lock:
            self._in_flight[span.context.span_id] = span

    def on_end(self, span: ReadableSpan) -> None:
        if not span.context or not span.context.trace_flags.sampled:
            return
        with self._lock:
            del self._in_flight[span.context.span_id]
            self.span_exporter.export((span,))

    def shutdown(self) -> None:
        self._stop_event.set()
        self._export_thread.join()
        self.span_exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    def export_in_flight_spans(self) -> None:
        """Export all in-flight spans without ending them.

        This method is primarily used for testing to ensure all spans
        are exported before assertions are made.
        """
        with self._lock:
            to_export = [self._readable_span(span) for span in self._in_flight.values()]
            if to_export:
                self.span_exporter.export(to_export)


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
            log_trace_url(span)

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
            log_trace_url(span)
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
