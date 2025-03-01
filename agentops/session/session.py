from __future__ import annotations

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


_SessionMixins = (AnalyticsSessionMixin, TelemetrySessionMixin)


class Session(*_SessionMixins, SessionBase):
    """Data container for session state with minimal public API"""

    # Use the session state descriptor
    _state_descriptor = session_state_field()

    def __init__(
        self,
        *,
        config: Config,
        **kwargs,
    ):
        """Initialize a Session with optional session_id."""
        # Initialize all properties
        self.config = config
        self._lock = threading.Lock()

        # Initialize mixins
        super().__init__(**kwargs)

        # Initialize state descriptor
        self._state = SessionState.INITIALIZING


        # Initialize session only if auto_start is True
        if self.auto_start:
            try:
                if not self.start():
                    self._state = SessionState.FAILED
                    if not self.config.fail_safe:
                        raise RuntimeError("Session.start() did not succeed", self)
                    logger.error("Session initialization failed")
                    return
            except Exception as e:
                if not self.config.fail_safe:
                    raise
                self._state = SessionState.FAILED
                logger.error(f"Failed to initialize session: {e}")
                self.end(SessionState.FAILED)

    # ------------------------------------------------------------------------------------------
    @property
    def state(self) -> SessionState:
        """Get the current session state."""
        return self._state

    @state.setter
    def state(self, value: SessionState):
        """Set the session state."""
        if isinstance(value, SessionState):
            self._state = value
        else:
            logger.warning(f"Invalid session state: {value}, must be a SessionState enum")
            self._state = SessionState.INDETERMINATE

    @property
    def is_running(self) -> bool:
        """Whether session is currently running"""
        return self._state.is_alive

    def end(self, end_state: Optional[SessionState] = None) -> None:
        """End the session"""
        with self._lock:
            if self._state.is_terminal:
                logger.debug(f"Session {self.session_id} already ended")
                return

            if end_state is not None:
                self._state = end_state


            self._end_timestamp = get_ISO_time()
            if self.span and self._end_timestamp is not None:
                # Only end the span if it hasn't been ended yet
                has_ended = hasattr(self.span, "end_time") and self.span.end_time is not None
                if not has_ended:
                    # End the span when setting end_timestamp
                    self.span.end(end_time=iso_to_unix_nano(self._end_timestamp))

            session_data = json.loads(self.json())
            if self.api:
                self.api.update_session(session_data)

            logger.debug(f"Session {self.session_id} ended with state {self._state}")

    def start(self):
        """Start the session"""
        with self._lock:
            if self._state != SessionState.INITIALIZING:
                logger.warning("Session already started")
                return False


            try:
                session_data = json.loads(self.json())
                if not self.api:
                    logger.error("API client not initialized")
                    return False

                self.jwt = self.api.create_session(session_data)

                logger.info(
                    colored(
                        f"\x1b[34mSession Replay: {self.session_url}\x1b[0m",
                        "blue",
                    )
                )

                self._state = SessionState.RUNNING

                logger.debug(f"[{self.session_id}] Session started successfully")
                return True

            except ApiServerException as e:
                if not self.config.fail_safe:
                    raise
                logger.error(f"[{self.session_id}] Could not start session - {e}")
                self._state = SessionState.FAILED
                return False

    # ------------------------------------------------------------------------------------------
    def __repr__(self) -> str:
        """String representation"""
        parts = [f"Session(id={self.session_id}, status={self._state}"]

        if self.tags:
            parts.append(f"tags={self.tags}")

        return ", ".join(parts) + ")"

    # ------------------------------------------------------------------------------------------
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
