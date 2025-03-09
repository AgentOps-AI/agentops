from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generator, Optional, List
from uuid import UUID

from opentelemetry.trace import Span, Status, StatusCode

from agentops.session.base import SessionBase
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
        if self.span:
            return trace_id_to_uuid(self.span.get_span_context().trace_id)
        return None


class TelemetrySessionMixin(TracedSession):
    """
    Mixin that adds telemetry and span-related functionality to a session
    """

    _span: Optional[Span]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.telemetry = SessionTracer(self)
        self._span = None

    def _start_session_telemetry(self) -> None:
        """Start telemetry for the session."""
        self.telemetry.start()

    def _end_session_telemetry(self) -> None:
        """Shutdown telemetry for the session."""
        self.telemetry.shutdown()

    # TODO I can't find any references that actually call this. 
    # def set_status(self, state: SessionState, reason: Optional[str] = None) -> None:
    #     """Update root span status based on session state."""
    #     if self._span is None:
    #         return

    #     if state.is_terminal:
    #         if state.name == "SUCCEEDED":
    #             self._span.set_status(Status(StatusCode.OK))
    #         elif state.name == "FAILED":
    #             self._span.set_status(Status(StatusCode.ERROR))
    #         else:
    #             self._span.set_status(Status(StatusCode.UNSET))

    #         if reason:
    #             self._span.set_attribute("session.end_reason", reason)

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
        try:
            if self._span and self._span.init_time:
                return self._ns_to_iso(self._span.init_time)  # type: ignore
        except AttributeError:
            return None

    @property
    def end_timestamp(self) -> Optional[str]:
        """Get the end timestamp from the span if available."""
        try:
            if self._span and self._span.end_time:
                return self._ns_to_iso(self._span.end_time)  # type: ignore
        except AttributeError:
            return None

    @property
    def span(self) -> Optional[Span]:
        """Get the span from the session."""
        if self._span:
            return self._span
        return None

    @property
    def spans(self) -> Generator[Any, None, None]:
        """Generator that yields all spans in the trace."""
        if self.span:
            yield self.span
            for child in getattr(self.span, "children", []):
                yield child
