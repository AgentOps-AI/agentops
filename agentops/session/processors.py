"""Span processors for AgentOps.

This module provides custom span processors for OpenTelemetry integration.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Protocol

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult, SpanProcessor

from agentops.logging import logger


class InFlightSpanProcessor(SpanProcessor):
    """
    Adapted from Prefect's implementation.
    (https://github.com/PrefectHQ/prefect/blob/main/src/prefect/telemetry/processors.py)

    Custom span processor that tracks in-flight spans and ensures they are exported
    during shutdown or when explicitly requested.
    """

    def __init__(self, exporter: SpanExporter, max_export_batch_size: int = 512, schedule_delay_millis: int = 5000):
        """Initialize the InFlightSpanProcessor.

        Args:
            exporter: The exporter to use for exporting spans
            max_export_batch_size: The maximum batch size for exporting spans
            schedule_delay_millis: The delay between scheduled exports in milliseconds
        """
        self._exporter = exporter
        self._max_export_batch_size = max_export_batch_size
        self._schedule_delay_millis = schedule_delay_millis
        self._lock = threading.Lock()
        self._in_flight_spans: Dict[int, ReadableSpan] = {}
        self._shutdown = False

    def on_start(self, span: ReadableSpan, parent_context=None) -> None:
        """Called when a span starts.

        Args:
            span: The span that is starting
            parent_context: The parent context for the span
        """
        # We don't need to do anything when a span starts
        pass

    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span ends. Adds the span to in-flight spans.

        Args:
            span: The span that is ending
        """
        if self._shutdown:
            return

        with self._lock:
            # Use span_id as the key for the in-flight spans dictionary
            self._in_flight_spans[span.context.span_id] = span

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush all spans to be exported.

        Args:
            timeout_millis: The maximum time to wait for the flush to complete in milliseconds

        Returns:
            True if the flush was successful, False otherwise
        """
        return self._process_spans(export_only=False, timeout_millis=timeout_millis)

    def _process_spans(self, export_only: bool = False, timeout_millis: int = 30000) -> bool:
        """Process spans by exporting them and optionally flushing the exporter.

        Args:
            export_only: If True, only export spans without flushing the exporter
            timeout_millis: The maximum time to wait for the flush to complete in milliseconds

        Returns:
            True if the operation was successful, False otherwise. Always returns True
            for export_only=True.
        """
        # Export all in-flight spans
        spans_to_export = []
        with self._lock:
            if self._in_flight_spans:
                spans_to_export = list(self._in_flight_spans.values())
                self._in_flight_spans.clear()

        if spans_to_export:
            try:
                result = self._exporter.export(spans_to_export)
                if result != SpanExportResult.SUCCESS:
                    logger.warning(f"Failed to export {len(spans_to_export)} spans: {result}")
            except Exception as e:
                logger.warning(f"Error exporting spans: {e}")

        # Flush the exporter if requested
        if export_only:
            return True

        # Try to flush the exporter
        try:
            return self._exporter.force_flush(timeout_millis)
        except AttributeError:
            # Exporter doesn't support force_flush, which is fine
            return True
        except Exception as e:
            logger.warning(f"Error flushing exporter: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown the processor and export all in-flight spans."""
        with self._lock:
            self._shutdown = True
            spans_to_export = list(self._in_flight_spans.values())
            self._in_flight_spans.clear()

        if spans_to_export:
            try:
                result = self._exporter.export(spans_to_export)
                if result != SpanExportResult.SUCCESS:
                    logger.warning(f"Failed to export {len(spans_to_export)} spans: {result}")
            except Exception as e:
                logger.warning(f"Error exporting spans: {e}")

        self._exporter.shutdown()
