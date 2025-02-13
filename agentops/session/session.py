from __future__ import annotations

import functools
import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from blinker import Signal
from opentelemetry import trace
from requests import Response

# from opentelemetry.context import attach, detach, set_value
# from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from termcolor import colored

from agentops.api.session import SessionApiClient
from agentops.config import TESTING, Config
from agentops.exceptions import ApiServerException
from agentops.helpers import filter_unjsonable, get_ISO_time
from agentops.logging import logger

# Define signals for session events
session_starting = Signal()
session_started = Signal()
session_initialized = Signal()
session_ending = Signal()
session_ended = Signal()


class SessionState(Enum):
    """
    Enum representing the possible states of a session.

    Attributes:
        SUCCESS: Indicates the session ended successfully.
        FAIL: Indicates the session failed.
        INDETERMINATE (default): Indicates the session ended with an indeterminate state.
                       This is the default state if not specified, e.g. if you forget to call end_session()
                       at the end of your program or don't pass it the end_state parameter
    """

    SUCCESS = "Success"
    FAIL = "Fail"
    INDETERMINATE = "Indeterminate"  # Default


@dataclass
class Session:
    """Data container for session state with minimal public API"""

    session_id: UUID
    config: Config
    tags: List[str] = field(default_factory=list)
    host_env: Optional[dict] = None
    token_cost: Decimal = field(default_factory=lambda: Decimal(0))
    end_state: str = field(default_factory=lambda: SessionState.INDETERMINATE.value)
    end_state_reason: Optional[str] = None
    jwt: Optional[str] = None
    video: Optional[str] = None
    event_counts: Dict[str, int] = field(
        default_factory=lambda: {"llms": 0, "tools": 0, "actions": 0, "errors": 0, "apis": 0}
    )
    is_running: bool = field(default=False)

    def __post_init__(self):
        """Initialize session components after dataclass initialization"""
        # Initialize session-specific components
        self._lock = threading.Lock()
        self._end_session_lock = threading.Lock()

        if self.config.api_key is None:
            raise ValueError("API key is required")

        self.api = SessionApiClient(self.config.endpoint, self.session_id, self.config.api_key)
        # Initialize session
        try:
            if not self._start_session():
                raise RuntimeError("Session._initialize() did not succeed", self)
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            self.end(SessionState.FAIL.value, f"Exception during initialization: {str(e)}")
        finally:
            # Signal session is initialized
            session_initialized.send(self, session_id=self.session_id)

    def _start_session(self) -> bool:
        """
        Manually starts the session
        This method should only be responsible to send signals (`session_starting` and `session_started`)
        and initialize the JWT.
        """
        with self._lock:
            # Signal session is starting
            session_starting.send(self, session_id=self.session_id)

            self.init_timestamp = get_ISO_time()

            try:
                session_data = asdict(self)
                success, jwt = self.api.create_session(session_data, parent_key=self.config.parent_key)
                if not success:
                    logger.error("Failed to create session")
                    return False

                self.jwt = jwt
                if jwt is None:
                    logger.debug("No JWT received in response")
                    return False
                logger.debug("Successfully received and set JWT")

                self.is_running = True

                logger.info(
                    colored(
                        f"\x1b[34mSession Replay: {self.session_url}\x1b[0m",
                        "blue",
                    )
                )

                # Signal session started after successful initialization
                session_started.send(self)

                logger.debug("Session started successfully")
                return True

            except ApiServerException as e:
                logger.error(f"Could not start session - {e}")
                return False

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

    def _get_token_cost(self, response: Response) -> Decimal:
        """Get token cost from response"""
        try:
            token_cost = response.json().get("token_cost", "unknown")
            if token_cost == "unknown" or token_cost is None:
                return Decimal(0)
            return Decimal(token_cost)
        except (ValueError, AttributeError):
            return Decimal(0)

    def _format_token_cost(self, token_cost: Decimal) -> str:
        """Format token cost for display"""
        return (
            "{:.2f}".format(token_cost)
            if token_cost == 0
            else "{:.6f}".format(token_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
        )

    def _get_analytics(self) -> Optional[Dict[str, Union[int, str]]]:
        """Get session analytics"""
        if not self.end_timestamp:
            self.end_timestamp = get_ISO_time()

        formatted_duration = self._format_duration(self.init_timestamp, self.end_timestamp)

        response = self.api.update_session(asdict(self))
        if not response:
            return None

        # Update token cost from API response
        token_cost = response.get("token_cost")
        if token_cost is not None:
            self.token_cost = Decimal(str(token_cost))

        return {
            "LLM calls": self.event_counts["llms"],
            "Tool calls": self.event_counts["tools"],
            "Actions": self.event_counts["actions"],
            "Errors": self.event_counts["errors"],
            "Duration": formatted_duration,
            "Cost": self._format_token_cost(self.token_cost),
        }

    @property
    def session_url(self) -> str:
        """URL to view this trace in the dashboard"""
        return f"{self.config.endpoint}/drilldown?session_id={self.session_id}"

    def end(self, end_state: Optional[str] = None, end_state_reason: Optional[str] = None, video: Optional[str] = None) -> None:
        """
        End the session and send final state to the API.

        Args:
            end_state (str, optional): The final state of the session. Options: Success, Fail, or Indeterminate.
            end_state_reason (str, optional): The reason for ending the session.
            video (str, optional): URL to a video recording of the session
        """
        with self._end_session_lock:
            if not self.is_running:
                logger.debug(f"Session {self.session_id} already ended or not started")
                return

            # Signal session is ending
            session_ending.send(self, session_id=self.session_id)

            # Update session state
            if end_state:
                self.end_state = end_state
            if end_state_reason:
                self.end_state_reason = end_state_reason
            if video:
                self.video = video

            self.end_timestamp = get_ISO_time()
            self.is_running = False

            # Get analytics before ending
            analytics = self._get_analytics()
            if analytics:
                logger.info("\nSession Analytics:")
                for key, value in analytics.items():
                    logger.info(f"{key}: {value}")

            # Signal session has ended
            session_ended.send(self, session_id=self.session_id)
            logger.debug(f"Session {self.session_id} ended with state {self.end_state}")

    def __repr__(self) -> str:
        """Return a string representation of the Session."""
        if self.is_running:
            status = "Running"
        elif self.end_timestamp:
            status = "Ended"
        else:
            status = "Not Started"

        tag_str = f", tags={self.tags}" if self.tags else ""
        end_state_str = f", end_state={self.end_state}" if self.end_timestamp else ""

        return f"Session(id={self.session_id}, status={status}{tag_str}{end_state_str})"

    def flush(self):
        raise NotImplementedError
