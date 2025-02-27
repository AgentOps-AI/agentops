"""Base class for objects with tracked lifecycles and span integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

if TYPE_CHECKING:
    from agentops.session.session import SessionState


# Import instrumentation to ensure signal handlers are registered
from agentops.helpers.time import iso_to_unix_nano
from agentops.sdk.types import ISOTimeStamp
from agentops.session.tracer import (SessionTelemetry,
                                        cleanup_session_tracer,
                                        setup_session_tracer)


@dataclass
class SessionTelemetryMixin:
    """Base class for objects with tracked start and end timestamps.

    This class provides the foundation for tracking the lifecycle of an object
    through its initialization and end timestamps, and handles OpenTelemetry
    span integration.
    """

    span: trace.Span | None = field(default=None, init=False, repr=False)  # The root span for the session

    telemetry: SessionTelemetry = field(default=None, repr=False, init=False)

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
        if hasattr(self.span, "init_time"):
            return self._ns_to_iso(self.span.init_time)  # type: ignore

    @init_timestamp.setter
    def init_timestamp(self, value: Optional[ISOTimeStamp]) -> None:
        """Set the initialization timestamp."""
        if value is not None and not isinstance(value, str):
            raise ValueError("Timestamp must be a string in ISO format")
        self._init_timestamp = value

    @property
    def end_timestamp(self) -> Optional[str]:
        """Get the end timestamp from the span if available, otherwise return stored value."""
        if hasattr(self.span, "end_time"):
            return self._ns_to_iso(self.span.end_time)  # type: ignore

    @end_timestamp.setter
    def end_timestamp(self, value: ISOTimeStamp) -> None:
        """Set the end timestamp."""
        if value is not None and not isinstance(value, str):
            raise ValueError("Timestamp must be a string in ISO format")
        self._end_timestamp = value
        if self.span:
            if value is not None:
                # End the span when setting end_timestamp
                self.span.end(end_time=iso_to_unix_nano(value))

    # ------------------------------------------------------------

    def set_status(self, state: SessionState, reason: Optional[str] = None) -> None:
        """Update root span status based on session state."""
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
