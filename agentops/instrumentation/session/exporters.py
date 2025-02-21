from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence
from uuid import uuid4

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from agentops.config import TESTING
from agentops.logging import logger

if TYPE_CHECKING:
    from agentops.session import Session


class BaseExporter(ABC):
    """Base class for session exporters with common functionality"""

    def __init__(self, session: Session):
        self.session = session
        self._is_shutdown = False

    def export(self, data: Sequence[Any]) -> SpanExportResult:
        """Template method for export implementation"""
        if self._is_shutdown:
            return SpanExportResult.SUCCESS

        try:
            if not data:
                return SpanExportResult.SUCCESS
            return self._export(data)
        except Exception as e:
            logger.error(f"Export failed: {e}")
            if TESTING:
                raise e
            return SpanExportResult.FAILURE

    @abstractmethod
    def _export(self, data: Sequence[Any]) -> SpanExportResult:
        """To be implemented by subclasses"""
        raise NotImplementedError

    def shutdown(self):
        """Shutdown the exporter"""
        self._is_shutdown = True

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        """Force flush any spans"""
        return True


class SessionLifecycleExporter(BaseExporter, SpanExporter):
    """Handles only session start/end events"""
    def _export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        session_events = []
        for span in spans:
            if span.name in ["session.start", "session.end"]:
                # Convert span data to dict properly
                span_data = {}
                if hasattr(span, "to_json"):
                    # Handle custom to_json implementations
                    json_data = span.to_json()
                    if isinstance(json_data, dict):
                        span_data.update(json_data)
                    else:
                        # Fall back to attributes if to_json doesn't return dict
                        span_data.update(span.attributes or {})
                else:
                    # Use span attributes directly
                    span_data.update(span.attributes or {})
                
                span_data["session_id"] = str(self.session.session_id)
                session_events.append(span_data)
        
        if session_events:
            try:
                self.session.api.create_events(session_events)
                return SpanExportResult.SUCCESS
            except Exception as e:
                logger.error(f"Failed to export session events: {e}")
                return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS


class RegularEventExporter(BaseExporter, SpanExporter):
    """Handles regular events (not session lifecycle)"""
    def _export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        events = []
        for span in spans:
            if span.name not in ["session.start", "session.end"]:
                # Convert span data to dict properly
                span_data = {}
                if hasattr(span, "to_json"):
                    # Handle custom to_json implementations
                    json_data = span.to_json()
                    if isinstance(json_data, dict):
                        span_data.update(json_data)
                    else:
                        # Fall back to attributes if to_json doesn't return dict
                        span_data.update(span.attributes or {})
                else:
                    # Use span attributes directly
                    span_data.update(span.attributes or {})
                
                span_data["session_id"] = str(self.session.session_id)
                events.append(span_data)
        
        if events:
            try:
                self.session.api.create_events(events)
                return SpanExportResult.SUCCESS
            except Exception as e:
                logger.error(f"Failed to export regular events: {e}")
                return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS
