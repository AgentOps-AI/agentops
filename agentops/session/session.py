from __future__ import annotations

import datetime
import json
import threading
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from opentelemetry.trace import Status, StatusCode
from termcolor import colored

from agentops.exceptions import ApiServerException
from agentops.helpers import get_ISO_time
from agentops.helpers.serialization import AgentOpsJSONEncoder
from agentops.helpers.time import iso_to_unix_nano
from agentops.logging import logger
from agentops.sdk.descriptors.classproperty import classproperty

from .base import SessionBase
from .mixin.analytics import AnalyticsSessionMixin
from .mixin.registry import SessionRegistryMixin
from .mixin.telemetry import TelemetrySessionMixin
from .state import SessionState
from .state import SessionStateDescriptor as session_state_field

if TYPE_CHECKING:
    from agentops.config import Config


class Session(SessionRegistryMixin, AnalyticsSessionMixin, TelemetrySessionMixin, SessionBase):
    """Data container for session state with minimal public API"""

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

        # Initialize state
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

    def __enter__(self) -> "Session":
        """Context manager entry point.

        Returns:
            The session instance for use in a with statement.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit point.

        Args:
            exc_type: The exception type if an exception was raised, None otherwise.
            exc_val: The exception value if an exception was raised, None otherwise.
            exc_tb: The exception traceback if an exception was raised, None otherwise.
        """
        if exc_type is not None:
            # End with error state if there was an exception
            self.end(SessionState.FAILED)
        else:
            # End with success state if no exception
            self.end(SessionState.SUCCEEDED)

    def __del__(self) -> None:
        """Ensure cleanup on garbage collection.

        This method is called by the garbage collector when the object is about to be destroyed.
        It ensures that all resources are properly cleaned up if the session hasn't been ended.
        """
        try:
            # Only perform cleanup if not in a terminal state
            if self._state != SessionState.SUCCEEDED and self._state != SessionState.FAILED:
                logger.debug(f"[{self.session_id}] Session garbage collected before being ended")
                self.end(SessionState.INDETERMINATE)
        except Exception as e:
            logger.warning(f"Error during Session.__del__: {e}")

    def end(self, state=SessionState.SUCCEEDED):
        """End the session with the given state.

        Args:
            state: The final state of the session. Defaults to SUCCEEDED.
        """
        with self._lock:
            # Early return if already in a terminal state
            if self._state == SessionState.SUCCEEDED or self._state == SessionState.FAILED:
                logger.debug(f"[{self.session_id}] Session already in terminal state: {self._state}")
                return

            # Set the state
            self._state = state

            # Update span status directly based on state
            if self._span:
                if state == SessionState.SUCCEEDED:
                    self._span.set_status(Status(StatusCode.OK))
                elif state == SessionState.FAILED:
                    self._span.set_status(Status(StatusCode.ERROR))
                else:
                    self._span.set_status(Status(StatusCode.UNSET))

                # End the span directly if it hasn't been ended yet and telemetry is not available
                if self._span.end_time is None and self.telemetry is None:
                    self._span.end()
                    logger.debug(f"[{self.session_id}] Ended span directly")

            # Unregister from cleanup
            super().end()

            logger.debug(f"[{self.session_id}] Session ended with state: {state}")

    def start(self):
        """Start the session"""
        with self._lock:
            super().start()

            # Update state
            self._state = SessionState.RUNNING

            logger.debug(f"[{self.session_id}] Session started")

    # Add current function to get default session
    @classproperty
    def current(cls) -> Optional[Session]:
        """Get the current active session.

        Returns:
            The current active session if exactly one session exists, otherwise None.
        """
        from .registry import get_current_session

        return get_current_session()

    @property
    def init_timestamp(self) -> str:
        """Get the initialization timestamp."""
        # First try to get it from the span
        span_timestamp = super().init_timestamp
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
