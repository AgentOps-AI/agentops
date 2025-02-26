"""Base class for objects with tracked lifecycles and span integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, Optional

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

if TYPE_CHECKING:
    from agentops.session.session import SessionState


# Import instrumentation to ensure signal handlers are registered
from agentops.telemetry.meters import SessionMeters
from agentops.telemetry.session import (SessionTelemetry,
                                        cleanup_session_tracer,
                                        setup_session_tracer)


@dataclass
class SessionTelemetryAdapter:
    """Base class for objects with tracked start and end timestamps.

    This class provides the foundation for tracking the lifecycle of an object
    through its initialization and end timestamps, and handles OpenTelemetry
    span integration.
    """

    span: trace.Span | None = field(default=None, init=False, repr=False)  # The root span for the session

    telemetry: Optional[SessionTelemetry] = field(default=None, repr=False, init=False)

    meters: Optional[SessionMeters] = field(default=None, repr=False, init=False)

    _init_timestamp: Optional[str] = field(default=None, repr=False, init=False)
    _end_timestamp: Optional[str] = field(default=None, repr=False, init=False)

    @staticmethod
    def _ns_to_iso(ns_time: Optional[int]) -> Optional[str]:
        """Convert nanosecond timestamp to ISO format."""
        if ns_time is None:
            return None
        seconds = ns_time / 1e9
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    # ------------------------------------------------------------

    @property
    def init_timestamp(self) -> Optional[str]:
        """Get the initialization timestamp."""
        """Get the end timestamp from the span if available, otherwise return stored value."""
        if self.span is not None and hasattr(self.span, "init_time"):
            return self._ns_to_iso(self.span.init_time)  # type: ignore
        return self._init_timestamp

    @init_timestamp.setter
    def init_timestamp(self, value: Optional[str]) -> None:
        """Set the initialization timestamp."""
        if value is not None and not isinstance(value, str):
            raise ValueError("Timestamp must be a string in ISO format")
        self._init_timestamp = value

    @property
    def end_timestamp(self) -> Optional[str]:
        """Get the end timestamp from the span if available, otherwise return stored value."""
        if self.span is not None and hasattr(self.span, "end_time"):
            return self._ns_to_iso(self.span.end_time)  # type: ignore
        return self._end_timestamp

    @end_timestamp.setter
    def end_timestamp(self, value: Optional[str]) -> None:
        """Set the end timestamp."""
        if value is not None and not isinstance(value, str):
            raise ValueError("Timestamp must be a string in ISO format")
        self._end_timestamp = value
        if self.span is not None and value is not None:
            self.span.set_attribute("session.end_timestamp", value)

    # ------------------------------------------------------------

    def set_status(self, state: SessionState, reason: Optional[str] = None) -> None:
        """Update root span status based on session state."""
        if self.span is None:
            return

        if state.is_terminal:
            if state.name == "SUCCEEDED":
                self.span.set_status(Status(StatusCode.OK))
            elif state.name == "FAILED":
                self.span.set_status(Status(StatusCode.ERROR))
            else:
                self.span.set_status(Status(StatusCode.UNSET))

            if reason:
                self.span.set_attribute("session.end_reason", reason)

    @property
    def spans(self):
        """Generator that yields all spans in the trace."""
        if self.span:
            yield self.span
            for child in getattr(self.span, "children", []):
                yield child

    @property
    def event_counts(self) -> Dict[str, int]:
        """Get the event counts."""
        if self.meters is None:
            return {}
        return {
            "llms": self.meters.llm_counter.get_value(name="gen_ai.operation.name", value="chat"),
            "tools": self.meters.tool_counter.get_value(name="gen_ai.operation.name", value="execute_tool"),
            "actions": self.meters.action_counter.get_value(name="gen_ai.operation.name", value="action"),
            "errors": self.meters.error_counter.get_value(name="error.type", value="_OTHER"),
        }
