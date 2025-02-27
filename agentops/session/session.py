from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Dict, List, Optional, Union
from uuid import UUID, uuid4

from opentelemetry import trace
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
from agentops.session.tracer import SessionTracer

from .state import SessionState
from .state import SessionStateDescriptor as session_state_field

if TYPE_CHECKING:
    from agentops.config import Config

from .signals import *


class Session:
    """Data container for session state with minimal public API"""

    # __slots__ = (
    #     'config', 'tags', 'host_env', 'end_state_reason', 'jwt', 'video', 
    #     'event_counts', 'state', 'auto_start', '_session_id', '_lock',
    #     'span', 'telemetry', '_init_timestamp', '_end_timestamp', 'api'
    # )


    state = session_state_field

    def __init__(
        self,
        config: Optional[Config] = None,
        tags: Optional[List[str]] = [],
        host_env: Optional[dict] = get_host_env(),
        end_state_reason: Optional[str] = None,
        jwt: Optional[str] = None,
        video: Optional[str] = None,
        event_counts: Optional[Dict[str, int]] = None,
        *,
        auto_start: bool = True,
        session_id: Optional[UUID] = None,
    ):
        """Initialize a Session with optional session_id."""
        # Initialize all properties
        self.config = config or default_config()
        self.tags = tags or []
        self.host_env = host_env or {}
        self.end_state_reason = end_state_reason
        self.jwt = jwt
        self.video = video
        self.event_counts = event_counts or {"llms": 0, "tools": 0, "actions": 0, "errors": 0, "apis": 0}
        self.auto_start = auto_start
        self._session_id = session_id or uuid4()
        self._lock = threading.Lock()
        
        # Fields from mixin
        self.span: Optional[Span] = None
        self.telemetry = None
        self._init_timestamp: Optional[str] = None
        self._end_timestamp: Optional[str] = None
        self.api = None
        
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
                self.end(str(SessionState.FAILED), f"Exception during initialization: {str(e)}")

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
    def token_cost(self) -> str:
        """
        Processes token cost based on the last response from the API.
        """
        try:
            # Get token cost from either response or direct value
            cost = Decimal(0)
            if self.api and self.api.last_response is not None:
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

    def end(
        self, end_state: Optional[str] = None, end_state_reason: Optional[str] = None, video: Optional[str] = None
    ) -> None:
        """End the session"""
        with self._lock:
            if self._state.is_terminal:
                logger.debug(f"Session {self.session_id} already ended")
                return

            # Update state before sending signal
            if end_state is not None:
                self._state = SessionState.from_string(end_state)
            if end_state_reason is not None:
                self.end_state_reason = end_state_reason
            if video is not None:
                self.video = video

            # Send signal with current state
            session_ending.send(
                self, session_id=self.session_id, end_state=str(self._state), end_state_reason=self.end_state_reason
            )

            self.end_timestamp = get_ISO_time()

            session_data = json.loads(self.json())
            if self.api:
                self.api.update_session(session_data)

            session_updated.send(self)
            session_ended.send(
                self, session_id=self.session_id, end_state=str(self._state), end_state_reason=self.end_state_reason
            )
            logger.debug(f"Session {self.session_id} ended with state {self._state}")

    def start(self):
        """Start the session"""
        with self._lock:
            if self._state != SessionState.INITIALIZING:
                logger.warning("Session already started")
                return False

            session_starting.send(self)
            self.init_timestamp = get_ISO_time() # The SPAN will retrieve this

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

    def flush(self):
        if self.api:
            self.api.update_session()
            session_updated.send(self)
        else:
            logger.warning("Cannot flush: API client not initialized")

    def _format_duration(self, start_time, end_time) -> str:
        """Format duration between two timestamps"""
        if not start_time or not end_time:
            return "0.0s"
            
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
        parts = [f"Session(id={self.session_id}, status={self._state}"]

        if self.tags:
            parts.append(f"tags={self.tags}")

        if self._state.is_terminal and self.end_state_reason:
            parts.append(f"reason='{self.end_state_reason}'")

        return ", ".join(parts) + ")"

    def add_tags(self, tags: List[str]) -> None:
        """Add tags to the session

        Args:
            tags: List of tags to add
        """
        if self._state.is_terminal:
            logger.warning(f"{self.session_id} Cannot add tags to ended session")
            return

        self.tags.extend(tags)
        session_updated.send(self)

    def dict(self) -> dict:
        """Convert session to dictionary, excluding private and non-serializable fields"""
        return {
            "session_id": str(self.session_id),  # Explicitly convert UUID to string
            "config": self.config.dict(),
            "tags": self.tags,
            "host_env": self.host_env,
            "state": str(self._state),
            "jwt": self.jwt,
            "video": self.video,
            "event_counts": self.event_counts,
            "init_timestamp": self.init_timestamp,
            "end_timestamp": self.end_timestamp,
        }

    def set_tags(self, tags: List[str]) -> None:
        """Set session tags, replacing existing ones

        Args:
            tags: List of tags to set
        """
        if self._state.is_terminal:
            logger.warning("Cannot set tags on ended session")
            return

        self.tags = tags
        session_updated.send(self)

    def json(self):
        return json.dumps(self.dict(), cls=AgentOpsJSONEncoder)

    # Methods from SessionTelemetryMixin below:

    @staticmethod
    def _ns_to_iso(ns_time: Optional[int]) -> Optional[str]:
        """Convert nanosecond timestamp to ISO format."""
        if ns_time is None:
            return None
        seconds = ns_time / 1e9
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    @property
    def session_id(self) -> UUID:
        """Get session_id from instance variable."""
        # Always return the stored session ID
        return self._session_id

    @property
    def init_timestamp(self) -> Optional[str]:
        """Get the initialization timestamp from the span if available."""
        if self.span and hasattr(self.span, "init_time"):
            return self._ns_to_iso(self.span.init_time)  # type: ignore
        return self._init_timestamp

    @init_timestamp.setter
    def init_timestamp(self, value: Optional[str]) -> None:
        """Set the initialization timestamp."""
        if value is not None and not isinstance(value, str):
            raise ValueError("Timestamp must be a string in ISO format")
        self._init_timestamp = value

    @property
    def end_timestamp(self) -> Optional[str]:
        """Get the end timestamp from the span if available, otherwise return stored value."""
        if self.span and hasattr(self.span, "end_time"):
            return self._ns_to_iso(self.span.end_time)  # type: ignore
        return self._end_timestamp

    @end_timestamp.setter
    def end_timestamp(self, value: Optional[str]) -> None:
        """Set the end timestamp."""
        if value is not None and not isinstance(value, str):
            raise ValueError("Timestamp must be a string in ISO format")
        self._end_timestamp = value
        if self.span and value is not None:
            # Only end the span if it hasn't been ended yet
            # Check if the span has end_time attribute and it's been set
            has_ended = hasattr(self.span, "end_time") and self.span.end_time is not None
            if not has_ended:
                # End the span when setting end_timestamp
                self.span.end(end_time=iso_to_unix_nano(value))

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

    @property
    def spans(self):
        """Generator that yields all spans in the trace."""
        if self.span:
            yield self.span
            for child in getattr(self.span, "children", []):
                yield child
