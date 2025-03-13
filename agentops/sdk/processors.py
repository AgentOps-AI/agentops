"""
Span processors for AgentOps SDK.

This module contains processors for OpenTelemetry spans.
"""

import copy
import threading
import time
from threading import Event, Lock, Thread
from typing import Any, Dict, List, Optional

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter
from termcolor import colored

import agentops.semconv as semconv
from agentops.logging import logger
from agentops.sdk.converters import trace_id_to_uuid, uuid_to_int16
from agentops.semconv.core import CoreAttributes


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
    """

    def __init__(self, app_url: str = "https://app.agentops.ai"):
        """
        Initialize the PrintSpanProcessor.

        Args:
            app_url: The base URL for the AgentOps dashboard.
        """
        self.app_url = app_url

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

        # Get the span kind from attributes
        span_kind = (
            span.attributes.get(semconv.SpanAttributes.AGENTOPS_SPAN_KIND, "unknown") if span.attributes else "unknown"
        )

        # Print basic information about the span
        logger.debug(f"Started span: {span.name} (kind: {span_kind})")

        # Special handling for session spans
        if span_kind == semconv.SpanKind.SESSION:
            trace_id = span.context.trace_id
            # Convert trace_id to hex string if it's not already
            if isinstance(trace_id, int):
                session_url = f"{self.app_url}/drilldown?session_id={trace_id_to_uuid(trace_id)}"
                logger.info(
                    colored(
                        f"\x1b[34mSession started: {session_url}\x1b[0m",
                        "light_green",
                    )
                )
        else:
            # Print basic information for other span kinds
            logger.debug(f"Ended span: {span.name} (kind: {span_kind})")

    def on_end(self, span: ReadableSpan) -> None:
        """
        Called when a span is ended.

        Args:
            span: The span that was ended.
        """
        # Skip if span is not sampled
        if not span.context or not span.context.trace_flags.sampled:
            return

        # Get the span kind from attributes
        span_kind = (
            span.attributes.get(semconv.SpanAttributes.AGENTOPS_SPAN_KIND, "unknown") if span.attributes else "unknown"
        )

        # Special handling for session spans
        if span_kind == semconv.SpanKind.SESSION:
            trace_id = span.context.trace_id
            # Convert trace_id to hex string if it's not already
            if isinstance(trace_id, int):
                session_url = f"{self.app_url}/drilldown?session_id={trace_id_to_uuid(trace_id)}"
                logger.info(
                    colored(
                        f"\x1b[34mSession Replay: {session_url}\x1b[0m",
                        "blue",
                    )
                )
        else:
            # Print basic information for other span kinds
            logger.debug(f"Ended span: {span.name} (kind: {span_kind})")

    def shutdown(self) -> None:
        """Shutdown the processor."""
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush the processor."""
        return True
