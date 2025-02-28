from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Generator, Any

from opentelemetry.trace import Span, Status, StatusCode

from agentops.helpers.time import iso_to_unix_nano
from agentops.session.state import SessionState


class TelemetrySessionMixin:
    """
    Mixin that adds telemetry and span-related functionality to a session
    """

    def __init__(self, *args, **kwargs):
        # Initialize span-related fields
        self.span = None  # Will be a Span object when set
        self.telemetry = None
        # Call super().__init__ if it exists
        super().__init__(*args, **kwargs) if hasattr(super(), '__init__') else None

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
        if self.span and hasattr(self.span, "init_time"):
            return self._ns_to_iso(self.span.init_time)  # type: ignore
        return None

    @property
    def end_timestamp(self) -> Optional[str]:
        """Get the end timestamp from the span if available."""
        if self.span and hasattr(self.span, "end_time"):
            return self._ns_to_iso(self.span.end_time)  # type: ignore
        return None

    @property
    def spans(self) -> Generator[Any, None, None]:
        """Generator that yields all spans in the trace."""
        if self.span:
            yield self.span
            for child in getattr(self.span, "children", []):
                yield child
