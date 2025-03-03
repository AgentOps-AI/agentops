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

        # Initialize state descriptor
        self._state = SessionState.INITIALIZING

        # Initialize span attribute
        self.span = None

        # Initialize api attribute
        self.api = getattr(config, "api", None)
        self.jwt = None
        self._end_timestamp = None

        # Initialize mixins
        super().__init__(**kwargs)

        # Initialize session only if auto_start is True
        if self.auto_start:
            self.start()

    def end(self):
        """End the session"""
        with self._lock:
            raise NotImplementedError

    def start(self):
        """Start the session"""
        with self._lock:
            raise NotImplementedError("Session.start() is not implemented")

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
