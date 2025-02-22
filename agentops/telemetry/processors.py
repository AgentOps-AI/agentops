from __future__ import annotations

import time
from threading import Event, Lock, Thread
from typing import Dict, Optional, Sequence

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from agentops.logging import logger


class LiveSpanProcessor(SpanProcessor):
    """Processor that handles live spans during session lifecycle.
    
    This processor is specifically designed for AgentOps session spans that need to be
    tracked and exported in real-time while they are still active. It works in two main contexts:

    1. Session Context:
       - Tracks spans created within a session context manager
       - Handles spans between __enter__ and __exit__ of SessionContextMixin
       - Ensures spans are exported even if session ends unexpectedly

    2. Operation Context:
       - Tracks spans created by SessionTelemetry.start_operation()
       - Handles nested operation spans within a session
       - Maintains parent-child relationships between spans

    Not suitable for:
    - Spans outside of a session context
    - System-level or global spans
    - Spans from other OpenTelemetry instrumentations
    - Spans that don't have a valid session_id attribute

    Example usage:
    ```python
    # Proper usage within session context
    with session:
        with session.start_operation("my_operation"):
            # Spans here are tracked by LiveSpanProcessor
            pass

    # Not suitable for
    tracer = trace.get_tracer(__name__)
    with tracer.start_span("global_span"):
        # This span should use a different processor
        pass
    ```

    Args:
        span_exporter: The exporter to use for sending spans
        export_interval_secs: How often to export live spans (default: 0.05s)
    """

    def __init__(self, span_exporter: SpanExporter, export_interval_secs: float = 0.05):
        self.span_exporter = span_exporter
        self._live_spans: Dict[int, Span] = {}
        self._lock = Lock()
        self._shutdown = Event()
        self._export_interval = export_interval_secs
        self._last_export_time = time.monotonic()
        
        # Start background export thread
        self._export_thread = Thread(target=self._export_live_spans, daemon=True)
        self._export_thread.start()

    def _export_live_spans(self) -> None:
        """Periodically export live spans"""
        while not self._shutdown.is_set():
            time.sleep(self._export_interval)
            
            current_time = time.monotonic()
            if current_time - self._last_export_time < self._export_interval:
                continue
                
            with self._lock:
                if not self._live_spans:
                    continue
                    
                spans_to_export = [
                    self._create_span_snapshot(span)
                    for span in self._live_spans.values()
                    if span and span.context and span.context.is_valid
                ]
                if spans_to_export:
                    try:
                        self.span_exporter.export(spans_to_export)
                        self._last_export_time = current_time
                    except Exception as e:
                        logger.debug(f"Failed to export live spans: {e}")

    def _create_span_snapshot(self, span: Span) -> ReadableSpan:
        """Create a snapshot of a live span"""
        readable = span._readable_span()
        readable._end_time = time.time_ns()
        readable._attributes = {
            **(readable._attributes or {}),
            "live": True,
        }
        return readable

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        """Track span when it starts"""
        if not span or not span.context or not span.context.is_valid:
            return
            
        with self._lock:
            self._live_spans[span.context.span_id] = span

    def on_end(self, span: ReadableSpan) -> None:
        """Handle span when it ends"""
        if not span or not span.context or not span.context.is_valid:
            return
            
        with self._lock:
            self._live_spans.pop(span.context.span_id, None)
            try:
                self.span_exporter.export((span,))
            except Exception as e:
                logger.debug(f"Failed to export completed span: {e}")

    def shutdown(self) -> None:
        """Gracefully shutdown the processor"""
        self._shutdown.set()
        self._export_thread.join(timeout=1.0)
        
        with self._lock:
            if self._live_spans:
                final_spans = [
                    self._create_span_snapshot(span)
                    for span in self._live_spans.values()
                    if span and span.context and span.context.is_valid
                ]
                try:
                    self.span_exporter.export(final_spans)
                except Exception as e:
                    logger.debug(f"Failed to export final spans during shutdown: {e}")
            self._live_spans.clear()
        
        self.span_exporter.shutdown()

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        """Force flush all spans"""
        with self._lock:
            if self._live_spans:
                spans_to_flush = [
                    self._create_span_snapshot(span)
                    for span in self._live_spans.values()
                    if span and span.context and span.context.is_valid
                ]
                try:
                    self.span_exporter.export(spans_to_flush)
                except Exception as e:
                    logger.debug(f"Failed to force flush spans: {e}")
                    return False
        return True 
