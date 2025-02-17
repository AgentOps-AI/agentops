from __future__ import annotations

import functools
import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from blinker import Signal
from opentelemetry import trace
from requests import Response
# from opentelemetry.context import attach, detach, set_value
# from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from termcolor import colored

from agentops import session
from agentops.api.session import SessionApiClient
from agentops.config import TESTING, Config
from agentops.exceptions import ApiServerException
from agentops.helpers import filter_unjsonable, get_ISO_time
from agentops.logging import logger
from agentops.helpers.serialization import AgentOpsJSONEncoder

# Define signals for session events
session_starting = Signal()
session_started = Signal()
session_initialized = Signal()
session_ending = Signal()
session_ended = Signal()
session_updated = Signal()


class SessionState(Enum):
    """Session state enumeration"""
    INITIALIZING = "Initializing"
    RUNNING = "Running"
    FAILED = "Failed"
    SUCCEEDED = "Succeeded"
    INDETERMINATE = "Indeterminate"

    def __str__(self) -> str:
        return self.value

    @property
    def is_terminal(self) -> bool:
        """Whether this is a terminal state"""
        return self in (self.FAILED, self.SUCCEEDED, self.INDETERMINATE)

    @property
    def is_alive(self) -> bool:
        """Whether the session is still active"""
        return self in (self.INITIALIZING, self.RUNNING)


@dataclass
class Session:
    """Data container for session state with minimal public API"""

    session_id: UUID
    config: Config
    tags: List[str] = field(default_factory=list)
    host_env: Optional[dict] = None
    _state: SessionState = field(default=SessionState.INITIALIZING)
    end_state_reason: Optional[str] = None
    jwt: Optional[str] = None
    video: Optional[str] = None
    event_counts: Dict[str, int] = field(
        default_factory=lambda: {"llms": 0, "tools": 0, "actions": 0, "errors": 0, "apis": 0}
    )

    @property
    def state(self) -> SessionState:
        """Get current session state"""
        return self._state

    @state.setter
    def state(self, value: Union[SessionState, str]) -> None:
        """Set session state
        
        Args:
            value: New state (SessionState enum or string)
        """
        if isinstance(value, str):
            try:
                value = SessionState(value)
            except ValueError:
                logger.warning(f"Invalid session state: {value}")
                value = SessionState.INDETERMINATE
        self._state = value

    @property
    def end_state(self) -> str:
        """Legacy property for backwards compatibility"""
        return str(self.state)

    @end_state.setter 
    def end_state(self, value: str) -> None:
        """Legacy setter for backwards compatibility"""
        self.state = value

    @property
    def is_running(self) -> bool:
        """Whether session is currently running"""
        return self.state.is_alive

    def __post_init__(self):
        """Initialize session components after dataclass initialization"""
        # Initialize session-specific components
        self._lock = threading.Lock()
        self._end_session_lock = threading.Lock()
        
        self._init_timestamp = None
        self._end_timestamp = None

        if self.config.api_key is None:
            self.state = SessionState.FAILED
            raise ValueError("API key is required")

        self.api = SessionApiClient(self.config.endpoint, self.session_id, self.config.api_key)
        
        # Initialize session
        try:
            if not self.start():
                self.state = SessionState.FAILED
                raise RuntimeError("Session._initialize() did not succeed", self)
        except Exception as e:
            self.state = SessionState.FAILED
            logger.error(f"Failed to initialize session: {e}")
            self.end(str(SessionState.FAILED), f"Exception during initialization: {str(e)}")
        finally:
            # Signal session is initialized
            session_initialized.send(self, session_id=self.session_id)
            

    @property
    def init_timestamp(self) -> str | None:
        """Get the initialization timestamp"""
        return self._init_timestamp
    

    @init_timestamp.setter
    def init_timestamp(self, value: str):
        """Set the initialization timestamp"""
        self._init_timestamp = value
        

    @property   
    def end_timestamp(self) -> str | None:
        """Get the end timestamp"""
        return self._end_timestamp
    
    @end_timestamp.setter
    def end_timestamp(self, value: str):
        """Set the end timestamp"""
        self._end_timestamp = value

    @property
    def token_cost(self) -> str:
        """
        Processes token cost based on the last response from the API.
        """
        try:
            # Get token cost from either response or direct value
            cost = Decimal(0)
            if self.api.last_response is not None:
                cost_value = self.api.last_response.json().get("token_cost", "unknown")
                if cost_value != "unknown" and cost_value is not None:
                    cost = Decimal(str(cost_value))

            # Format the cost
            return (
                "{:.2f}".format(cost)
                if cost == 0
                else "{:.6f}".format(cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
            )
        except (ValueError, AttributeError):
            return "0.00"


    @property
    def analytics(self) -> Optional[Dict[str, Union[int, str]]]:
        """Get session analytics"""
        formatted_duration = self._format_duration(self.init_timestamp, self.end_timestamp)

        return {
            "LLM calls": self.event_counts["llms"],
            "Tool calls": self.event_counts["tools"],
            "Actions": self.event_counts["actions"],
            "Errors": self.event_counts["errors"],
            "Duration": formatted_duration,
            "Cost": self.token_cost,
        }

    @property
    def session_url(self) -> str:
        """URL to view this trace in the dashboard"""
        return f"{self.config.endpoint}/drilldown?session_id={self.session_id}"

    def end(
        self, 
        end_state: Optional[str] = None,
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None
    ) -> None:
        """End the session"""
        with self._end_session_lock:
            if self.state.is_terminal:
                logger.debug(f"Session {self.session_id} already ended")
                return

            session_ending.send(self, session_id=self.session_id)

            if end_state is not None:
                self.state = end_state
            if end_state_reason is not None:
                self.end_state_reason = end_state_reason
            if video is not None:
                self.video = video

            self.end_timestamp = get_ISO_time()

            session_data = json.loads(
                json.dumps(asdict(self), cls=AgentOpsJSONEncoder)
            )
            self.api.update_session(session_data)

            session_updated.send(self, session_id=self.session_id)
            session_ended.send(self, session_id=self.session_id)
            logger.debug(f"Session {self.session_id} ended with state {self.state}")

    def start(self):
        """Start the session"""
        with self._lock:
            session_starting.send(self, session_id=self.session_id)
            self.init_timestamp = get_ISO_time()

            try:
                session_data = json.loads(
                    json.dumps(asdict(self), cls=AgentOpsJSONEncoder)
                )
                self.jwt = self.api.create_session(
                    session_data, 
                    parent_key=self.config.parent_key
                )

                logger.info(
                    colored(
                        f"\x1b[34mSession Replay: {self.session_url}\x1b[0m",
                        "blue",
                    )
                )

                session_started.send(self)
                logger.debug("Session started successfully")
                self.state = SessionState.RUNNING
                return True

            except ApiServerException as e:
                logger.error(f"Could not start session - {e}")
                self.state = SessionState.FAILED
                return False

    def flush(self):
        self.api.update_session()
        session_updated.send(self)

    def _format_duration(self, start_time, end_time) -> str:
        """Format duration between two timestamps"""
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        duration = end - start

        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if hours > 0:
            parts.append(f"{int(hours)}h")
        if minutes > 0:
            parts.append(f"{int(minutes)}m")
        parts.append(f"{seconds:.1f}s")

        return " ".join(parts)

    ##########################################################################################
    def __repr__(self) -> str:
        """String representation"""
        parts = [f"Session(id={self.session_id}, status={self.state}"]
        
        if self.tags:
            parts.append(f"tags={self.tags}")
            
        if self.state.is_terminal and self.end_state_reason:
            parts.append(f"reason='{self.end_state_reason}'")
            
        return ", ".join(parts) + ")"

    def add_tags(self, tags: List[str]) -> None:
        """Add tags to the session
        
        Args:
            tags: List of tags to add
        """
        self.tags.extend(tags)

    def set_tags(self, tags: List[str]) -> None:
        """Set session tags, replacing existing ones
        
        Args:
            tags: List of tags to set
        """
        self.tags = tags
