from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from opentelemetry.trace import Span, Status, StatusCode
from termcolor import colored

from agentops.api.session import SessionApiClient
from agentops.config import Config, default_config
from agentops.exceptions import ApiServerException
from agentops.helpers import get_ISO_time
from agentops.helpers.serialization import AgentOpsJSONEncoder
from agentops.helpers.system import get_host_env
from agentops.helpers.time import iso_to_unix_nano
from agentops.logging import logger

from .mixin.analytics import AnalyticsSessionMixin
from .mixin.telemetry import TelemetrySessionMixin
from .signals import *
from .state import SessionState
from .state import SessionStateDescriptor as session_state_field

if TYPE_CHECKING:
    from agentops.config import Config


_SessionMixins = (AnalyticsSessionMixin, TelemetrySessionMixin)


class Session(*_SessionMixins):
    """Data container for session state with minimal public API"""

    # Use the session state descriptor
    _state_descriptor = session_state_field()

    def __init__(
        self,
        tags: Optional[List[str]] = [],
        *,
        jwt: Optional[str] = None,
        auto_start: bool = True,
        session_id: Optional[UUID] = None,  # TODO: Define use cases for initializing session with a specific ID
        host_env: Optional[dict] = get_host_env(),
        config: Optional[Config] = None,
    ):
        """Initialize a Session with optional session_id."""
        # Initialize all properties
        self.config = config or default_config()
        self.tags = tags or []
        self.host_env = host_env or {}
        self.jwt = jwt
        self.auto_start = auto_start
        self._session_id = session_id or uuid4()
        self._lock = threading.Lock()
        self.api = None

        # Initialize mixins
        super().__init__()

        # Initialize state descriptor
        self._state = SessionState.INITIALIZING

        # Initialize session-specific components
        if self.config.api_key is None:
            self._state = SessionState.FAILED
            if not self.config.fail_safe:
                raise ValueError("API key is required")
            logger.error("API key is required")
            return

        self.api = SessionApiClient(self)

        # Signal session is initialized
        session_initialized.send(self)

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
                self.end(str(SessionState.FAILED))

    # ------------------------------------------------------------------------------------------
    @property
    def state(self) -> SessionState:
        """Get the current session state."""
        return self._state

    @state.setter
    def state(self, value):
        """Set the session state."""
        if isinstance(value, SessionState):
            self._state = value
        else:
            # Try to convert string to SessionState
            try:
                self._state = SessionState.from_string(str(value))
            except ValueError:
                logger.warning(f"Invalid session state: {value}")
                self._state = SessionState.INDETERMINATE

    @property
    def session_url(self) -> str:
        """URL to view this trace in the dashboard"""
        return f"{self.config.endpoint}/drilldown?session_id={self.session_id}"

    @property
    def is_running(self) -> bool:
        """Whether session is currently running"""
        return self._state.is_alive

    def _map_end_state(self, state: str) -> SessionState:
        """Map common end state strings to SessionState enum values"""
        state_map = {
            "Success": SessionState.SUCCEEDED,
            "SUCCEEDED": SessionState.SUCCEEDED,
            "Succeeded": SessionState.SUCCEEDED,
            "Fail": SessionState.FAILED,
            "FAILED": SessionState.FAILED,
            "Failed": SessionState.FAILED,
            "Indeterminate": SessionState.INDETERMINATE,
            "INDETERMINATE": SessionState.INDETERMINATE,
        }
        try:
            # First try to map the string directly
            return state_map.get(state, SessionState(state))
        except ValueError:
            logger.warning(f"Invalid end state: {state}, using INDETERMINATE")
            return SessionState.INDETERMINATE

    def end(self, end_state: Optional[str] = None) -> None:
        """End the session"""
        with self._lock:
            if self._state.is_terminal:
                logger.debug(f"Session {self.session_id} already ended")
                return

            # Update state before sending signal
            if end_state is not None:
                self._state = SessionState.from_string(end_state)

            # Send signal with current state
            session_ending.send(self, session_id=self.session_id, end_state=str(self._state))

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

            session_updated.send(self)
            session_ended.send(self, session_id=self.session_id, end_state=str(self._state))
            logger.debug(f"Session {self.session_id} ended with state {self._state}")

    def start(self):
        """Start the session"""
        with self._lock:
            if self._state != SessionState.INITIALIZING:
                logger.warning("Session already started")
                return False

            session_starting.send(self)
            # self.init_timestamp = get_ISO_time() # The SPAN will retrieve this

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

                # Set state before sending signal so registry sees correct state
                self._state = SessionState.RUNNING

                # Send session_started signal with self as sender
                session_started.send(self)
                logger.debug(f"[{self.session_id}] Session started successfully")
                return True

            except ApiServerException as e:
                if not self.config.fail_safe:
                    raise
                logger.error(f"[{self.session_id}] Could not start session - {e}")
                self._state = SessionState.FAILED
                return False

    def __repr__(self) -> str:
        """String representation"""
        parts = [f"Session(id={self.session_id}, status={self._state}"]

        if self.tags:
            parts.append(f"tags={self.tags}")

        return ", ".join(parts) + ")"

    # ------------------------------------------------------------------------------------------

    @property
    def session_id(self) -> UUID:
        """Get session_id from instance variable."""
        # Always return the stored session ID
        return self._session_id

    # ------------------------------------------------------------------------------------------

    def dict(self) -> dict:
        """Convert session to dictionary, excluding private and non-serializable fields"""
        return {
            "session_id": str(self.session_id),  # Explicitly convert UUID to string
            "config": self.config.dict(),
            "tags": self.tags,
            "host_env": self.host_env,
            "state": str(self._state),
            "jwt": self.jwt,
            "init_timestamp": self.init_timestamp,
            "end_timestamp": self.end_timestamp,
        }

    def json(self):
        return json.dumps(self.dict(), cls=AgentOpsJSONEncoder)
