"""
Span processors for AgentOps SDK.

This module contains processors for OpenTelemetry spans.
"""

import copy
import threading
import time
from typing import Dict, List, Optional, Any

from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from agentops.logging import logger


class LiveSpanProcessor(SpanProcessor):
    """
    A span processor that exports spans immediately when requested,
    and also exports snapshots of in-flight spans.
    
    This processor tracks spans that are currently in progress and exports snapshots
    of them periodically. This allows for real-time visibility of long-running spans
    before they complete.
    
    Inspired by Prefect's InFlightSpanProcessor.
    """
    
    def __init__(
        self, 
        exporter: SpanExporter, 
        max_export_batch_size: int = 512, 
        schedule_delay_millis: int = 5000
    ):
        """
        Initialize the processor.
        
        Args:
            exporter: The exporter to use
            max_export_batch_size: Max export batch size (unused in this implementation)
            schedule_delay_millis: How often to export snapshots in milliseconds
        """
        self._exporter = exporter
        self._lock = threading.Lock()
        self._in_flight_spans: Dict[int, Span] = {}  # Dictionary to track active spans
        
        # Setup periodic export
        self._stop_event = threading.Event()
        self._export_interval = schedule_delay_millis / 1000  # Convert to seconds
        self._export_thread = threading.Thread(target=self._export_periodically, daemon=True)
        self._export_thread.start()
    
    def _export_periodically(self) -> None:
        """Periodically export snapshots of in-flight spans."""
        while not self._stop_event.is_set():
            time.sleep(self._export_interval)
            self.export_in_flight_spans()
    
    def _create_readable_snapshot(self, span: Span) -> ReadableSpan:
        """
        Create a readable snapshot of a span that's still in progress.
        
        Args:
            span: The span to create a snapshot of
            
        Returns:
            A readable snapshot of the span
        """
        try:
            # Try to get a readable span directly if the span supports it
            if hasattr(span, "_readable_span"):
                readable = span._readable_span()
            else:
                # Otherwise, use the span as is (it might already be a ReadableSpan)
                readable = span
            
            # Make a copy to avoid modifying the original
            readable_copy = copy.deepcopy(readable)
            
            # Set a temporary end time (current time)
            if hasattr(readable_copy, "_end_time"):
                readable_copy._end_time = time.time_ns()
            
            # Mark this as an in-flight span
            # We can't modify the attributes directly, but we can add a custom attribute
            # to the span using the set_attribute method if available
            if hasattr(span, "set_attribute"):
                # Use the original span's method to set the attribute
                # This is safer than trying to modify the attributes dictionary directly
                span.set_attribute("in_flight", True)
            
            return readable_copy
        except Exception as e:
            logger.warning(f"Error creating readable snapshot: {e}")
            return span  # Return the original span as a fallback
    
    def on_start(self, span: Span, parent_context=None) -> None:
        """
        Called when a span starts.
        
        Adds the span to the in-flight spans dictionary.
        
        Args:
            span: The span that is starting
            parent_context: Optional parent context
        """
        # Only track sampled spans that have a context with a span_id
        span_context = getattr(span, "context", None)
        if span_context is not None and hasattr(span_context, "span_id"):
            span_id = span_context.span_id
            if span_id is not None:
                with self._lock:
                    self._in_flight_spans[span_id] = span
                    
                # If the span has immediate_export=True, export it immediately
                if hasattr(span, "attributes") and span.attributes and span.attributes.get("export.immediate"):
                    self._export_snapshot(span)
    
    def _export_snapshot(self, span: Span) -> None:
        """
        Export a snapshot of an in-flight span.
        
        Args:
            span: The span to export a snapshot of
        """
        try:
            readable_snapshot = self._create_readable_snapshot(span)
            self._exporter.export([readable_snapshot])
        except Exception as e:
            logger.warning(f"Error exporting span snapshot: {e}")
    
    def on_end(self, span: ReadableSpan) -> None:
        """
        Called when a span ends.
        
        Removes the span from the in-flight dictionary and exports it normally.
        
        Args:
            span: The span that is ending
        """
        # Remove from in-flight spans if it was there
        span_context = getattr(span, "context", None)
        if span_context is not None and hasattr(span_context, "span_id"):
            span_id = span_context.span_id
            if span_id is not None:
                with self._lock:
                    if span_id in self._in_flight_spans:
                        del self._in_flight_spans[span_id]
        
        # Export the span normally
        try:
            self._exporter.export([span])
        except Exception as e:
            logger.warning(f"Error exporting finished span: {e}")
    
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """
        Force flush all spans to be exported.
        
        Args:
            timeout_millis: Timeout in milliseconds
            
        Returns:
            True if the flush succeeded, False otherwise
        """
        # First export any in-flight spans
        self.export_in_flight_spans()
        
        try:
            result = self._exporter.force_flush(timeout_millis)
            return result
        except Exception as e:
            logger.warning(f"Error flushing spans: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shut down the processor and stop the export thread."""
        self._stop_event.set()
        if self._export_thread.is_alive():
            self._export_thread.join(timeout=1.0)  # Give it a second to finish
            
        # Export any remaining spans
        self.export_in_flight_spans()
        
        try:
            self._exporter.shutdown()
        except Exception as e:
            logger.warning(f"Error shutting down exporter: {e}")
            
    def export_in_flight_spans(self) -> None:
        """Export snapshots of all in-flight spans."""
        with self._lock:
            if not self._in_flight_spans:
                return
                
            to_export = []
            for span in self._in_flight_spans.values():
                try:
                    readable_snapshot = self._create_readable_snapshot(span)
                    to_export.append(readable_snapshot)
                except Exception as e:
                    logger.warning(f"Error creating snapshot for span: {e}")
            
            if to_export:
                try:
                    self._exporter.export(to_export)
                except Exception as e:
                    logger.warning(f"Error exporting span snapshots: {e}") 