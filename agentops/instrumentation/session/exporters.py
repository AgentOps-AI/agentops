from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, Sequence
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
        self._shutdown = threading.Event()
        self._export_lock = threading.Lock()

    def export(self, data: Sequence[Any]) -> SpanExportResult:
        """Template method for export implementation"""
        if self._shutdown.is_set():
            return SpanExportResult.SUCCESS

        with self._export_lock:
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
        """Mark the exporter as shutdown"""
        self._shutdown.set()

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        return True



class SessionLifecycleExporter(BaseExporter, SpanExporter):
    """Handles only session start/end events"""
    def _export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        session_events = []
        for span in spans:
            if span.name in ["session.start", "session.end"]:
                session_events.append(span.to_json()) # TODO: Add session_id ?
        
        if session_events:
            try:
                # Send events to your backend/storage
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
                events.append(span.to_json()) # TODO: Add session_id ?
        
        if events:
            try:
                # Send events to your backend/storage
                self.session.api.create_events(events)
                return SpanExportResult.SUCCESS
            except Exception as e:
                logger.error(f"Failed to export regular events: {e}")
                return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS
