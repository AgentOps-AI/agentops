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
from agentops.sdk.descriptors.classproperty import classproperty

from .base import SessionBase
from .mixin.analytics import AnalyticsSessionMixin
from .mixin.telemetry import TelemetrySessionMixin
from .state import SessionState
from .state import SessionStateDescriptor as session_state_field

if TYPE_CHECKING:
    from agentops.config import Config


class Session(AnalyticsSessionMixin, TelemetrySessionMixin, SessionBase):
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

    def end(self):
        """End the session"""
        with self._lock:
            self.telemetry.shutdown()

    def start(self):
        """Start the session"""
        with self._lock:
            self.telemetry.start()

    # Add current function to get default session
    @classproperty
    def current(cls) -> Optional[Session]:
        """Get the current active session.

        Returns:
            The current active session if exactly one session exists, otherwise None.
        """
        from .registry import get_current_session
        return get_current_session()

            # 
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
