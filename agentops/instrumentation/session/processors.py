from __future__ import annotations

import time
from threading import Event, Lock, Thread
from typing import Dict, Optional, Sequence

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from agentops.logging import logger


class InFlightSpanProcessor(SpanProcessor):
    """Processor that handles in-flight spans during shutdown"""

    def __init__(self, span_exporter: SpanExporter, export_interval_secs: float = 0.05):
        self.span_exporter = span_exporter
        self._in_flight: Dict[int, Span] = {}
        self._lock = Lock()
        self._shutdown = Event()
        self._export_interval = export_interval_secs
        self._last_export_time = time.monotonic()  # Use monotonic time
        
        # Start background export thread
        self._export_thread = Thread(target=self._export_in_flight_spans, daemon=True)
        self._export_thread.start()

    def _export_in_flight_spans(self) -> None:
        """Periodically export in-flight spans"""
        while not self._shutdown.is_set():
            time.sleep(self._export_interval)
            
            # Skip if no spans or if last export was too recent
            current_time = time.monotonic()
            if current_time - self._last_export_time < self._export_interval:
                continue
                
            with self._lock:
                if not self._in_flight:
                    continue
                    
                # Create readable snapshots of in-flight spans
                spans_to_export = [
                    self._create_span_snapshot(span)
                    for span in self._in_flight.values()
                    if span and span.context and span.context.is_valid  # Guard against None
                ]
                if spans_to_export:
                    try:
                        self.span_exporter.export(spans_to_export)
                        self._last_export_time = current_time
                    except Exception as e:
                        logger.debug(f"Failed to export in-flight spans: {e}")

    def _create_span_snapshot(self, span: Span) -> ReadableSpan:
        """Create a snapshot of an in-flight span"""
        readable = span._readable_span()  # Get the ReadableSpan version
        readable._end_time = time.time_ns()  # Still use time_ns() for span timestamps
        readable._attributes = {
            **(readable._attributes or {}),
            "in_flight": True,
        }
        return readable

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        """Track span when it starts"""
        if not span or not span.context or not span.context.is_valid:
            return
            
        with self._lock:
            self._in_flight[span.context.span_id] = span

    def on_end(self, span: ReadableSpan) -> None:
        """Handle span when it ends"""
        if not span or not span.context or not span.context.is_valid:
            return
            
        with self._lock:
            # Remove from in-flight tracking
            self._in_flight.pop(span.context.span_id, None)
            # Export the completed span
            try:
                self.span_exporter.export((span,))
            except Exception as e:
                logger.debug(f"Failed to export completed span: {e}")

    def shutdown(self) -> None:
        """Gracefully shutdown the processor"""
        self._shutdown.set()
        self._export_thread.join(timeout=1.0)
        
        # Final export of any remaining spans
        with self._lock:
            if self._in_flight:
                final_spans = [
                    self._create_span_snapshot(span)
                    for span in self._in_flight.values()
                    if span and span.context and span.context.is_valid  # Guard against None
                ]
                try:
                    self.span_exporter.export(final_spans)
                except Exception as e:
                    logger.debug(f"Failed to export final spans during shutdown: {e}")
            self._in_flight.clear()
        
        self.span_exporter.shutdown()

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        """Force flush all spans"""
        with self._lock:
            if self._in_flight:
                spans_to_flush = [
                    self._create_span_snapshot(span)
                    for span in self._in_flight.values()
                    if span and span.context and span.context.is_valid  # Guard against None
                ]
                try:
                    self.span_exporter.export(spans_to_flush)
                except Exception as e:
                    logger.debug(f"Failed to force flush spans: {e}")
                    return False
        return True 
