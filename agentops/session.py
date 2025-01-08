from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
import threading
import json

from termcolor import colored

from .config import Configuration
from .enums import EndState
from .event import Event, ErrorEvent
from .helpers import get_ISO_time, filter_unjsonable
from .log_config import logger
from .http_client import HttpClient
from .exceptions import ApiServerException

# Global list to track active sessions
active_sessions: List[Session] = []

@dataclass
class Session:
    """
    Represents a session of events, with a start and end state.
    
    Args:
        session_id (UUID): The session id is used to record particular runs.
        config (Configuration): The configuration object for the session.
        tags (List[str], optional): Tags for grouping/sorting.
        host_env (dict, optional): Host and environment data.
    """
    session_id: UUID
    config: Configuration
    tags: List[str] = field(default_factory=list)
    host_env: Optional[dict] = None
    token_cost: Decimal = field(default_factory=lambda: Decimal(0))
    end_state: str = field(default_factory=lambda: EndState.INDETERMINATE.value)
    end_state_reason: Optional[str] = None
    end_timestamp: Optional[str] = None
    jwt: Optional[str] = None
    video: Optional[str] = None
    event_counts: Dict[str, int] = field(
        default_factory=lambda: {
            "llms": 0, 
            "tools": 0, 
            "actions": 0, 
            "errors": 0,
            "apis": 0
        }
    )
    init_timestamp: str = field(default_factory=get_ISO_time)
    is_running: bool = field(default=True)

    def __post_init__(self):
        """Initialize session manager and start session"""
        self._lock = threading.Lock()
        self._end_session_lock = threading.Lock()
        
        # Start session to get JWT
        if not self._start_session():
            self.is_running = False
            raise Exception("Failed to start session")

        # Add to global active sessions list
        active_sessions.append(self)

        logger.info(
            colored(
                f"\x1b[34mSession Replay: {self.session_url}\x1b[0m",
                "blue",
            )
        )

    def _start_session(self) -> bool:
        """Initialize session and get JWT"""
        with self._lock:
            payload = {"session": self.__dict__}
            serialized_payload = json.dumps(filter_unjsonable(payload)).encode("utf-8")

            try:
                res = HttpClient.post(
                    f"{self.config.endpoint}/v2/create_session",
                    serialized_payload,
                    api_key=self.config.api_key,
                    parent_key=self.config.parent_key,
                )
            except ApiServerException as e:
                logger.error(f"Could not start session - {e}")
                return False

            logger.debug(res.body)

            if res.code != 200:
                return False

            jwt = res.body.get("jwt", None)
            self.jwt = jwt
            if jwt is None:
                return False

            return True

    def record(self, event: Union[Event, ErrorEvent]) -> None:
        """Record an event"""
        self._manager.record_event(event)

    def add_tags(self, tags: List[str]) -> None:
        """Append to session tags"""
        if not self.is_running:
            return

        if not (isinstance(tags, list) and all(isinstance(item, str) for item in tags)):
            if isinstance(tags, str):
                tags = [tags]

        # Add new unique tags
        for tag in tags:
            if tag not in self.tags:
                self.tags.append(tag)

        self._manager.update_session()

    def set_tags(self, tags: List[str]) -> None:
        """Replace session tags"""
        if not self.is_running:
            return

        if not (isinstance(tags, list) and all(isinstance(item, str) for item in tags)):
            if isinstance(tags, str):
                tags = [tags]

        self.tags = tags.copy()
        self._manager.update_session()

    @property
    def session_url(self) -> str:
        """Returns the URL for this session in the AgentOps dashboard."""
        assert self.session_id, "Session ID is required"
        return f"https://app.agentops.ai/drilldown?session_id={self.session_id}"

    def end_session(
        self,
        end_state: str = EndState.INDETERMINATE.value,
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None,
    ) -> Optional[Decimal]:
        """End the session"""
        if not self.is_running:
            return None

        with self._end_session_lock:
            self.is_running = False
            self.end_state = end_state
            self.end_state_reason = end_state_reason
            self.video = video
            self.end_timestamp = get_ISO_time()

            # Remove from active sessions
            if self in active_sessions:
                active_sessions.remove(self)

            # Update session on server
            payload = {"session": self.__dict__}
            try:
                res = HttpClient.post(
                    f"{self.config.endpoint}/v2/update_session",
                    json.dumps(filter_unjsonable(payload)).encode("utf-8"),
                    jwt=self.jwt,
                )
                if res.code == 200 and "token_cost" in res.body:
                    self.token_cost = Decimal(str(res.body["token_cost"]))
                    return self.token_cost
            except ApiServerException as e:
                logger.error(f"Could not end session - {e}")

            return None

class SessionManager:
    """Handles session operations and state management"""
    
    def __init__(self, session_state):
        self._state = session_state
        self._lock = threading.Lock()
        self._end_session_lock = threading.Lock()

    def start_session(self) -> bool:
        """Initialize session and get JWT"""
        with self._lock:
            payload = {"session": self._state.__dict__}
            serialized_payload = json.dumps(filter_unjsonable(payload)).encode("utf-8")

            try:
                res = HttpClient.post(
                    f"{self._state.config.endpoint}/v2/create_session",
                    serialized_payload,
                    api_key=self._state.config.api_key,
                    parent_key=self._state.config.parent_key,
                )
            except ApiServerException as e:
                return logger.error(f"Could not start session - {e}")

            logger.debug(res.body)

            if res.code != 200:
                return False

            jwt = res.body.get("jwt", None)
            self._state.jwt = jwt
            if jwt is None:
                return False

            return True

    def record_event(self, event: Union[Event, ErrorEvent]) -> None:
        """Record an event"""
        if not self._state.is_running:
            return

        # Set session_id on event
        event.session_id = self._state.session_id

        # Update event counts
        if event.event_type in self._state.event_counts:
            self._state.event_counts[event.event_type] += 1

    def update_session(self) -> None:
        """Update session state on server"""
        if not self._state.is_running:
            return

        with self._lock:
            payload = {"session": self._state.__dict__}
            try:
                HttpClient.post(
                    f"{self._state.config.endpoint}/v2/update_session",
                    json.dumps(filter_unjsonable(payload)).encode("utf-8"),
                    jwt=self._state.jwt,
                )
            except ApiServerException as e:
                logger.error(f"Could not update session - {e}")

    def reauthorize_jwt(self) -> Optional[str]:
        """Get new JWT token"""
        with self._lock:
            payload = {"session_id": self._state.session_id}
            serialized_payload = json.dumps(filter_unjsonable(payload)).encode("utf-8")
            res = HttpClient.post(
                f"{self._state.config.endpoint}/v2/reauthorize_jwt",
                serialized_payload,
                self._state.config.api_key,
            )

            if res.code != 200:
                return None

            jwt = res.body.get("jwt", None)
            self._state.jwt = jwt
            return jwt
