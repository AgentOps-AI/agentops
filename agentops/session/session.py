from __future__ import annotations

import functools
import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from opentelemetry import trace

# from opentelemetry.context import attach, detach, set_value
# from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from termcolor import colored

from agentops.config import TESTING, Configuration
from agentops.event import Event
from agentops.exceptions import ApiServerException
from agentops.helpers import filter_unjsonable, get_ISO_time, safe_serialize
from agentops.http_client import HttpClient, Response
from agentops.log_config import logger
from agentops.session.signals import (
    event_recorded,
    event_recording,
    session_ended,
    session_ending,
    session_initialized,
    session_initializing,
    session_started,
    session_starting,
    session_updated,
)
from agentops.telemetry import InstrumentedBase


class EndState(Enum):
    """
    Enum representing the possible end states of a session.

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
class Session(InstrumentedBase):
    """Data container for session state with minimal public API"""

    session_id: UUID
    config: Configuration
    tags: List[str] = field(default_factory=list)
    host_env: Optional[dict] = None
    token_cost: Decimal = field(default_factory=lambda: Decimal(0))
    end_state: str = field(default_factory=lambda: EndState.INDETERMINATE.value)
    end_state_reason: Optional[str] = None
    jwt: Optional[str] = None
    video: Optional[str] = None
    event_counts: Dict[str, int] = field(
        default_factory=lambda: {"llms": 0, "tools": 0, "actions": 0, "errors": 0, "apis": 0}
    )
    is_running: bool = field(default=False)

    def __post_init__(self):
        """Initialize session components after dataclass initialization"""
        # First create the session span
        super().__post_init__()

        # Then initialize session-specific components
        self._lock = threading.Lock()
        self._end_session_lock = threading.Lock()

        # Initialize session
        try:
            session_initializing.send(self)
            if not self._initialize():
                raise RuntimeError("Session._initialize() did not succeed", self)
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            self.end(EndState.FAIL.value, f"Exception during initialization: {str(e)}")
        finally:
            # Signal session is initialized
            session_initialized.send(self, session_id=self.session_id)

    def _cleanup(self):
        """Clean up session resources"""
        pass

    def _initialize(self) -> bool:
        """Initialize session components"""
        try:
            # Start the session which will get JWT and initialize everything
            if not self._start_session():
                return False

            logger.info(colored(f"\x1b[34mSession Replay: {self.session_url}\x1b[0m", "blue"))

            return True

        except Exception as e:
            if TESTING:
                raise e
            logger.error(f"Failed to initialize session: {e}")
            return False

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

            payload = {"session": asdict(self)}
            logger.debug(f"Prepared session payload: {payload}")

            try:
                serialized_payload = json.dumps(filter_unjsonable(payload)).encode("utf-8")
                logger.debug("Sending create session request with payload: %s", serialized_payload)
                res = HttpClient.post(
                    f"{self.config.endpoint}/v2/create_session",
                    serialized_payload,
                    api_key=self.config.api_key,
                    parent_key=self.config.parent_key,
                )
                assert res.code == 200, f"Failed to start session - {res.status}: {res.body}"

            except ApiServerException as e:
                logger.error(f"Could not start session - {e}")
                return False
            else:  # If no exception is raised
                self.is_running = True

                # Signal session started after successful initialization
                session_started.send(self)

            jwt = res.body.get("jwt", None)
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

            logger.debug("Session started successfully")
            return True

    # def _setup_logging(self) -> bool:
    #     """Set up logging for the session"""
    #     try:
    #         self._log_exporter = SessionLogExporter(session=self)
    #         self._log_handler, self._log_processor = setup_session_telemetry(self.session_id, self._log_exporter)
    #         logger.addHandler(self._log_handler)
    #         return True
    #     except Exception as e:
    #         logger.error(f"Failed to setup logging: {e}")
    #         return False

    def record(self, event: Event, flush_now=False) -> None:
        """Record an event in this trace"""
        if not self.is_running:
            return

        # Set session ID on event - it shouldn't already be set; this Event should still be
        assert not event.session_id, "ProgrammingError: Event already has a session_id"
        event.session_id = self.session_id

        try:
            # Make sure we're using the session's span context when recording the event
            if not self.span:
                logger.error("No span available for recording event")
                return

            with trace.use_span(self.span, end_on_exit=False):
                # Signal event recording is starting
                event_recording.send(self, event=event)

                # Signal event has been recorded - this triggers span creation
                event_recorded.send(self, event=event, flush_now=flush_now)

        except Exception as e:
            logger.error(f"Error recording event: {e}")
            if TESTING:
                raise e

    def add_tags(self, tags: List[str]) -> None:
        """
        Append to session tags at runtime.
        """
        if not self.is_running:
            return

        if not (isinstance(tags, list) and all(isinstance(item, str) for item in tags)):
            if isinstance(tags, str):
                tags = [tags]

        # Initialize tags if None
        if self.tags is None:
            self.tags = []

        # Add new tags that don't exist
        for tag in tags:
            if tag not in self.tags:
                self.tags.append(tag)

        # Update session state immediately
        self._update_session()

    def set_tags(self, tags):
        """Set session tags, replacing any existing tags"""
        if not self.is_running:
            return

        if not (isinstance(tags, list) and all(isinstance(item, str) for item in tags)):
            if isinstance(tags, str):
                tags = [tags]

        # Set tags directly
        self.tags = tags.copy()  # Make a copy to avoid reference issues

        # Update session state immediately
        self._update_session()

    def end(
        self,
        end_state: str = EndState.INDETERMINATE.value,
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None,
    ) -> Union[Decimal, None]:
        with self._end_session_lock:
            # Add check to prevent multiple ends
            assert self.is_running, "Session is not running"

            if not any(end_state == state.value for state in EndState):
                raise ValueError("Invalid end_state. Please use one of the EndState")

            self.end_state = end_state
            self.end_state_reason = end_state_reason

            try:
                if video is not None:
                    self.video = video

                # Clean up trace components
                self._cleanup()

                # Send ending signal before setting is_running to False
                session_ending.send(self, end_state=end_state, end_state_reason=end_state_reason)

                # Set is_running to False after sending ending signal
                self.is_running = False

                try:
                    self._update_session()
                except:
                    # We're setting back is_running to True to allow retrying
                    # !! Though this is not the best practice
                    self.is_running = True
                    raise

                # Log final analytics
                # FIXME: Hilarious, but self.get_analytics() is actually what notifies session updates hence ending the session
                if analytics_stats := self.get_analytics():
                    logger.info(
                        f"Session Stats - "
                        f"{colored('Duration:', attrs=['bold'])} {analytics_stats['Duration']} | "
                        f"{colored('Cost:', attrs=['bold'])} ${analytics_stats['Cost']} | "
                        f"{colored('LLMs:', attrs=['bold'])} {analytics_stats['LLM calls']} | "
                        f"{colored('Tools:', attrs=['bold'])} {analytics_stats['Tool calls']} | "
                        f"{colored('Actions:', attrs=['bold'])} {analytics_stats['Actions']} | "
                        f"{colored('Errors:', attrs=['bold'])} {analytics_stats['Errors']}"
                    )
                    logger.info(colored(f"\x1b[34mSession Replay: {self.session_url}\x1b[0m", "blue"))

                    return self.token_cost

            except Exception as e:
                logger.exception(f"Error during session end: {e}")
            finally:
                # Send ended signal only once
                session_ended.send(self, end_state=end_state, end_state_reason=end_state_reason)

    def _reauthorize_jwt(self) -> Union[str, None]:
        with self._lock:
            payload = {"session_id": self.session_id}
            try:
                serialized_payload = safe_serialize(payload).encode("utf-8")
                res = HttpClient.post(
                    f"{self.config.endpoint}/v2/reauthorize_jwt",
                    serialized_payload,
                    self.config.api_key,
                )
                if not res:
                    return None
                jwt = res.body.get("jwt")
                self.jwt = jwt
                return jwt
            except Exception as e:
                logger.error(f"Failed to reauthorize JWT: {e}")
                return None

    def _update_session(self) -> None:
        """Update session state on the server"""

        with self._lock:
            # Emit session updated signal

            payload = {"session": asdict(self)}

            try:
                self.__update_session_response = HttpClient.post(
                    f"{self.config.endpoint}/v2/update_session",
                    json.dumps(filter_unjsonable(payload)).encode("utf-8"),
                    jwt=self.jwt,
                    api_key=self.config.api_key,  # Add API key here
                )
            except ApiServerException as e:
                logger.error(f"Could not update session - {e}")
            else:
                session_updated.send(self, session_id=self.session_id)

    def create_agent(self, name, agent_id):
        """Create a new agent in the session"""
        if not self.is_running:
            return
        if agent_id is None:
            agent_id = str(uuid4())

        payload = {
            "id": agent_id,
            "name": name,
        }

        serialized_payload = safe_serialize(payload).encode("utf-8")
        try:
            HttpClient.post(
                f"{self.config.endpoint}/v2/create_agent",
                serialized_payload,
                jwt=self.jwt,
                api_key=self.config.api_key,
            )
        except ApiServerException as e:
            logger.error(f"Could not create agent - {e}")
            return

        return agent_id

    def patch(self, func):
        """Decorator to patch a function with the session"""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            kwargs["session"] = self
            return func(*args, **kwargs)

        return wrapper

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
        token_cost = response.body.get("token_cost", "unknown")
        if token_cost == "unknown" or token_cost is None:
            return Decimal(0)
        return Decimal(token_cost)

    def _format_token_cost(self, token_cost: Decimal) -> str:
        """Format token cost for display"""
        return (
            "{:.2f}".format(token_cost)
            if token_cost == 0
            else "{:.6f}".format(token_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
        )

    def get_analytics(self) -> Optional[Dict[str, Any]]:
        """Get session analytics"""
        formatted_duration = self._format_duration(self.init_timestamp, self.end_timestamp)

        self.token_cost = self._get_token_cost(self.__update_session_response)

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
        return f"https://app.agentops.ai/drilldown?session_id={self.session_id}"

    def end_session(self, *args, **kwargs):
        """
        Deprecated: Use end() instead.
        Kept for backward compatibility.
        """
        return self.end(*args, **kwargs)

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

    def _create_span(self) -> None:
        """Create session span using session_id as trace_id"""
        # Convert session_id UUID to trace_id int
        trace_id = int(str(self.session_id).replace("-", ""), 16)

        # Create context with our trace ID
        context = trace.SpanContext(
            trace_id=trace_id,
            span_id=0,
            is_remote=False,
            # Don't sample the Session span itself, but allow Events to inherit the trace_id
            trace_flags=trace.TraceFlags.DEFAULT,
        )

        # Set the context before calling super()
        token = trace.set_span_in_context(context)
        with trace.use_span(token):
            super()._create_span()

    def force_flush(self):
        return
        # self.flush()
