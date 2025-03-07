from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generator, Optional, List
from uuid import UUID

from opentelemetry.trace import Span, Status, StatusCode

from agentops.session.base import SessionBase
from agentops.session.state import SessionState
from agentops.session.tracer import SessionTracer


def trace_id_to_uuid(trace_id: int) -> UUID:
    # Convert the trace_id to a 32-character hex string
    trace_id_hex = format(trace_id, "032x")

    # Format as UUID string (8-4-4-4-12)
    uuid_str = (
        f"{trace_id_hex[0:8]}-{trace_id_hex[8:12]}-{trace_id_hex[12:16]}-{trace_id_hex[16:20]}-{trace_id_hex[20:32]}"
    )

    # Create UUID object
    return UUID(uuid_str)


class TracedSession(SessionBase):
    _span: Optional[Span]
    telemetry: SessionTracer

    @property
    def session_id(self):
        """Returns the Trace ID as a UUID"""
        if not (span := getattr(self, "_span", None)):
            return None
        return trace_id_to_uuid(span.get_span_context().trace_id)


class TelemetrySessionMixin(TracedSession):
    """
    Mixin that adds telemetry and span-related functionality to a session
    """

    _span: Optional[Span]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) if hasattr(super(), "__init__") else None
        self.telemetry = SessionTracer(self)
        self._span = None

    def set_status(self, state: SessionState, reason: Optional[str] = None) -> None:
        """Update root span status based on session state."""
        if self._span is None:
            return

        if state.is_terminal:
            if state.name == "SUCCEEDED":
                self._span.set_status(Status(StatusCode.OK))
            elif state.name == "FAILED":
                self._span.set_status(Status(StatusCode.ERROR))
            else:
                self._span.set_status(Status(StatusCode.UNSET))

            if reason:
                self._span.set_attribute("session.end_reason", reason)

    @staticmethod
    def _ns_to_iso(ns_time: Optional[int]) -> Optional[str]:
        """Convert nanosecond timestamp to ISO format."""
        if ns_time is None:
            return None
        seconds = ns_time / 1e9
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    @property
    def init_timestamp(self) -> Optional[str]:
        """Get the initialization timestamp from the span if available."""
        if self._span and hasattr(self._span, "init_time"):
            return self._ns_to_iso(self._span.init_time)  # type: ignore
        return None

    @property
    def end_timestamp(self) -> Optional[str]:
        """Get the end timestamp from the span if available."""
        if self._span and hasattr(self._span, "end_time"):
            return self._ns_to_iso(self._span.end_time)  # type: ignore
        return None

    def get_spans(self) -> List[Span]:
        """Get all spans in the trace."""
        result = []
        if self._span:
            result.append(self._span)
            # Add any child spans if available
            if hasattr(self._span, "children"):
                result.extend(getattr(self._span, "children", []))
        return result
