from __future__ import annotations

import datetime
import json
import threading
from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

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
from .mixin.state import SessionStateMixin
from .mixin.telemetry import TelemetrySessionMixin
from .state import SessionState

if TYPE_CHECKING:
    from agentops.config import Config


class SessionReportingMixin(AnalyticsSessionMixin, TelemetrySessionMixin):
    pass

class Session(SessionRegistryMixin, SessionReportingMixin, SessionStateMixin, SessionBase):
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
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            # End with error state if there was an exception
            self.end(SessionState.FAILED)
        else:
            # End with success state if no exception
            self.end(SessionState.SUCCEEDED)

    def __del__(self) -> None:
        try:
            # Only perform cleanup if not in a terminal state
            if not self.is_terminal():
                logger.debug(f"[{self.session_id}] Session garbage collected before being ended")
                self.end(SessionState.INDETERMINATE)
        except Exception as e:
            logger.warning(f"Error during Session.__del__: {e}")

    def start(self):
        """Start the session"""
        with self._lock:
            # explicitly call mixin methods for clear execution order
            # Running state is set by the `SessionStateMixin`
            self._start_session_registry()
            self._start_session_state()
            self._start_session_telemetry()
            
            logger.debug(f"[{self.session_id}] Session started")

    def end(self, state: Union[SessionState, str] = SessionState.SUCCEEDED):
        """End the session with the given state.

        Args:
            state: The final state of the session. Defaults to SUCCEEDED.
        """
        with self._lock:
            # explicitly call mixin methods for clear execution order
            self._end_session_registry()
            self._end_session_state(state)
            self._end_session_telemetry()
            
            logger.debug(f"[{self.session_id}] Session ended with state: {state}")

    def create_agent(self, name, agent_id):
        """Deprecated method to manually create an agent in older versions of the SDK."""
        # this method is called explicitly by CrewAI and should fail silently
        pass

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
            "state": str(self.state),
            "init_timestamp": self.init_timestamp,
            "end_timestamp": self.end_timestamp,
        }

    def json(self):
        return json.dumps(self.dict(), cls=AgentOpsJSONEncoder)
