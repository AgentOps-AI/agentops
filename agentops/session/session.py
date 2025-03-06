from __future__ import annotations

import datetime
import json
import threading
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from termcolor import colored

from agentops.exceptions import ApiServerException
from agentops.helpers import get_ISO_time
from agentops.helpers.serialization import AgentOpsJSONEncoder
from agentops.helpers.time import iso_to_unix_nano
from agentops.logging import logger

from .base import SessionBase
from .mixin.analytics import AnalyticsSessionMixin
from .mixin.telemetry import TelemetrySessionMixin
from .state import SessionState
from .state import SessionStateDescriptor as session_state_field

if TYPE_CHECKING:
    from agentops.config import Config


class Session(AnalyticsSessionMixin, TelemetrySessionMixin, SessionBase):
    """Data container for session state with minimal public API

    The Session class manages the lifecycle of a session, including span creation,
    telemetry data collection, and cleanup. Sessions should ideally be explicitly
    ended using the end() method, but will be automatically cleaned up when they
    go out of scope via the __del__ method.

    Note: While automatic cleanup via __del__ is provided as a safety mechanism,
    it's still recommended to explicitly call end() when done with a session to
    ensure timely cleanup and proper state recording.
    """

    def __init__(
        self,
        *,
        config: Config,
        **kwargs,
    ):
        """Initialize a Session with optional session_id."""
        # Pass the config to the base class initialization
        # This ensures the config is properly set in kwargs before super().__init__ is called
        kwargs["config"] = config

        # Initialize state descriptor
        self._state = SessionState.INITIALIZING

        # Initialize lock
        self._lock = threading.Lock()

        # Set default init_timestamp
        self._init_timestamp = datetime.datetime.utcnow().isoformat() + "Z"

        # Initialize mixins and base class
        super().__init__(**kwargs)

        # Initialize session only if auto_start is True
        if self.auto_start:
            self.start()

    def __del__(self) -> None:
        """
        Cleanup method called during garbage collection.

        Ensures the session is properly ended and spans are exported
        when the session object goes out of scope without an explicit
        end() call.
        """
        try:
            # Check if session is still running
            if hasattr(self, "_state") and self._state != SessionState.SUCCEEDED and self._state != SessionState.FAILED:
                # Log that we're ending the session during garbage collection
                logger.info(f"Session {getattr(self, 'session_id', 'unknown')} being ended during garbage collection")

                # End the session with appropriate state
                self.end(state=SessionState.INDETERMINATE)
        except Exception as e:
            # Log the exception but don't raise it (exceptions in __del__ are ignored)
            logger.warning(f"Error during Session.__del__ for session {getattr(self, 'session_id', 'unknown')}: {e}")

    def end(self, state=None):
        """End the session

        This method ends the session, shutting down the telemetry tracer and
        setting the final state of the session.

        Args:
            state: Optional final state for the session. If not provided, defaults to SUCCEEDED.
        """
        with self._lock:
            self.telemetry.shutdown()
            if state is not None:
                self._state = state
            else:
                self._state = SessionState.SUCCEEDED

    def start(self):
        """Start the session"""
        with self._lock:
            self.telemetry.start()

    @property
    def init_timestamp(self) -> str:
        """Get the initialization timestamp."""
        # First try to get it from the span
        span_timestamp = super().init_timestamp if hasattr(super(), "init_timestamp") else None
        # If not available, use our default timestamp
        return span_timestamp or self._init_timestamp

    def dict(self) -> dict:
        """Convert session to dictionary, excluding private and non-serializable fields"""
        return {
            "session_id": str(self.session_id),  # Explicitly convert UUID to string
            "config": self.config.dict(),
            "tags": self.tags,
            "host_env": self.host_env,
            "state": str(self._state),
            "init_timestamp": self.init_timestamp,
            "end_timestamp": self.end_timestamp,
        }

    def json(self):
        return json.dumps(self.dict(), cls=AgentOpsJSONEncoder)
