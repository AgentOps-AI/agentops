from __future__ import annotations

import asyncio
import functools
import json
import threading
import time
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Sequence, Union

from agentops.session.api import SessionApi

try:
    from typing import DefaultDict  # Python 3.9+
except ImportError:
    from typing_extensions import DefaultDict  # Python 3.8 and below

from uuid import UUID, uuid4
from weakref import WeakSet

from opentelemetry import trace
from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter, SpanExportResult
from termcolor import colored

from agentops.config import Configuration
from agentops.enums import EndState, EventType
from agentops.event import ErrorEvent, Event
from agentops.exceptions import ApiServerException
from agentops.helpers import filter_unjsonable, get_ISO_time, safe_serialize
from agentops.http_client import HttpClient, Response
from agentops.log_config import logger
from agentops.session.exporter import SessionExporter


class SessionDict(DefaultDict):
    session_id: UUID
    # --------------
    config: Configuration
    end_state: str = EndState.INDETERMINATE.value
    end_state_reason: Optional[str] = None
    end_timestamp: Optional[str] = None
    # Create a counter dictionary with each EventType name initialized to 0
    event_counts: Dict[str, int]
    host_env: Optional[dict] = None
    init_timestamp: str  # Will be set to get_ISO_time() during __init__
    is_running: bool = False
    jwt: Optional[str] = None
    tags: Optional[List[str]] = None
    video: Optional[str] = None

    def __init__(self, **kwargs):
        kwargs.setdefault("event_counts", {event_type.value: 0 for event_type in EventType})
        kwargs.setdefault("init_timestamp", get_ISO_time())
        super().__init__(**kwargs)

class Session(SessionDict, SessionExporterMixIn):
    """
    Represents a session of events, with a start and end state.

    Args:
        session_id (UUID): The session id is used to record particular runs.
        config (Configuration): The configuration object for the session.
        tags (List[str], optional): Tags that can be used for grouping or sorting later. Examples could be ["GPT-4"].
        host_env (dict, optional): A dictionary containing host and environment data.

    Attributes:
        init_timestamp (str): The ISO timestamp for when the session started.
        end_timestamp (str, optional): The ISO timestamp for when the session ended. Only set after end_session is called.
        end_state (str, optional): The final state of the session. Options: "Success", "Fail", "Indeterminate". Defaults to "Indeterminate".
        end_state_reason (str, optional): The reason for ending the session.
        session_id (UUID): Unique identifier for the session.
        tags (List[str]): List of tags associated with the session for grouping and filtering.
        video (str, optional): URL to a video recording of the session.
        host_env (dict, optional): Dictionary containing host and environment data.
        config (Configuration): Configuration object containing settings for the session.
        jwt (str, optional): JSON Web Token for authentication with the AgentOps API.
        token_cost (Decimal): Running total of token costs for the session.
        event_counts (dict): Counter for different types of events:
            - llms: Number of LLM calls
            - tools: Number of tool calls
            - actions: Number of actions
            - errors: Number of errors
            - apis: Number of API calls
        session_url (str, optional): URL to view the session in the AgentOps dashboard.
        is_running (bool): Flag indicating if the session is currently active.
    """

    def __init__(
        self,
        session_id: UUID,
        config: Configuration,
        tags: Optional[List[str]] = None,
        host_env: Optional[dict] = None,
    ):
        self.end_timestamp = None
        self.end_state: Optional[str] = "Indeterminate"
        self.session_id = session_id
        self.init_timestamp = get_ISO_time()
        self.tags: List[str] = tags or []
        self.video: Optional[str] = None
        self.end_state_reason: Optional[str] = None
        self.host_env = host_env
        self.config = config
        self.jwt = None
        self._lock = threading.Lock()
        self._end_session_lock = threading.Lock()
        self.token_cost: Decimal = Decimal(0)
        self._session_url: str = ""
        self.event_counts = {
            "llms": 0,
            "tools": 0,
            "actions": 0,
            "errors": 0,
            "apis": 0,
        }
        # self.session_url: Optional[str] = None

        # Set creation timestamp
        self.__create_ts = time.monotonic()

        self.api = SessionApi(self)

        self._locks = {
            "lifecycle": threading.Lock(),  # Controls session lifecycle operations
            "update_session": threading.Lock(),  # Protects session state updates"
            "events": threading.Lock(),  # Protects event queue operations
            "session": threading.Lock(),  # Protects session state updates
            "tags": threading.Lock(),  # Protects tag modifications
            "api": threading.Lock(),  # Protects API calls
        }

        # Start session first to get JWT
        self._start_session()
        if not self.is_running:
            return

    def set_video(self, video: str) -> None:
        """
        Sets a url to the video recording of the session.

        Args:
            video (str): The url of the video recording
        """
        self.video = video

    def end_session(
        self,
        end_state: str = "Indeterminate",
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None,
    ) -> Union[Decimal, None]:
        with self._end_session_lock:
            if not self.is_running:
                return None

            if not any(end_state == state.value for state in EndState):
                logger.warning("Invalid end_state. Please use one of the EndState enums")
                return None

            try:
                # Force flush any pending spans before ending session
                self.exporter.flush()

                # 1. Set shutdown flag on exporter first
                self.exporter.shutdown()

                # 2. Set session end state
                self.end_timestamp = get_ISO_time()
                self.end_state = end_state
                self.end_state_reason = end_state_reason
                if video is not None:
                    self.video = video

                # 3. Mark session as not running before cleanup
                self.is_running = False

                # 5. Final session update
                if not (analytics_stats := self.get_analytics()):
                    return None

                analytics = (
                    f"Session Stats - "
                    f"{colored('Duration:', attrs=['bold'])} {analytics_stats['Duration']} | "
                    f"{colored('Cost:', attrs=['bold'])} ${analytics_stats['Cost']} | "
                    f"{colored('LLMs:', attrs=['bold'])} {analytics_stats['LLM calls']} | "
                    f"{colored('Tools:', attrs=['bold'])} {analytics_stats['Tool calls']} | "
                    f"{colored('Actions:', attrs=['bold'])} {analytics_stats['Actions']} | "
                    f"{colored('Errors:', attrs=['bold'])} {analytics_stats['Errors']}"
                )
                logger.info(analytics)

            except Exception as e:
                logger.exception(f"Error during session end: {e}")
            finally:
                active_sessions.remove(self)  # First thing, get rid of the session

                logger.info(
                    colored(
                        f"\x1b[34mSession Replay: {self.session_url}\x1b[0m",
                        "blue",
                    )
                )
            return self.token_cost

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

    def record(self, event: Union[Event, ErrorEvent], flush_now=False):
        """Record an event using OpenTelemetry spans"""
        if not self.is_running:
            return

        # Ensure event has all required base attributes
        if not hasattr(event, "id"):
            event.id = uuid4()
        if not hasattr(event, "init_timestamp"):
            event.init_timestamp = get_ISO_time()
        if not hasattr(event, "end_timestamp") or event.end_timestamp is None:
            event.end_timestamp = get_ISO_time()

        # Delegate to OTEL-specific recording logic
        self._record_otel_event(event, flush_now)

    def _send_event(self, event):
        """Direct event sending for testing"""
        try:
            payload = {
                "events": [
                    {
                        "id": str(event.id),
                        "event_type": event.event_type,
                        "init_timestamp": event.init_timestamp,
                        "end_timestamp": event.end_timestamp,
                        "data": filter_unjsonable(event.__dict__),
                    }
                ]
            }

            HttpClient.post(
                f"{self.config.endpoint}/v2/create_events",
                json.dumps(payload).encode("utf-8"),
                jwt=self.jwt,
            )
        except Exception as e:
            logger.error(f"Failed to send event: {e}")

    def _reauthorize_jwt(self) -> Union[str, None]:
        with self._lock:
            payload = {"session_id": self.session_id}
            serialized_payload = json.dumps(filter_unjsonable(payload)).encode("utf-8")
            res = HttpClient.post(
                f"{self.config.endpoint}/v2/reauthorize_jwt",
                serialized_payload,
                self.config.api_key,
            )

            logger.debug(res.body)

            if res.code != 200:
                return None

            jwt = res.body.get("jwt", None)
            self.jwt = jwt
            return jwt

    def _start_session(self):
        """
        Should either return `self` or raise an exception if the session could not be started.
        TODO: Determine the side effects of:
        - `bool` not being returned anymore
        - An exception being raised: what are the side effects?
        """
        with self._locks["lifecycle"]:
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
                return logger.error(f"Could not start session - {e}")

            logger.debug(res.body)

            if res.code != 200:
                return False

            jwt = res.body.get("jwt", None)
            self.jwt = jwt
            if jwt is None:
                return False

            logger.info(
                colored(
                    f"\x1b[34mSession Replay: {self.session_url}\x1b[0m",
                    "blue",
                )
            )

            return True

    def _update_session(self) -> None:
        """Update session state on the server"""
        with self._locks[
            "update_session"
        ]:  # TODO: Determine whether we really need to lock here: are incoming calls coming from other threads?
            if not self.is_running:
                return
            self.api.create_session()

    def create_agent(self, name, agent_id):  # FIXME: Move call to SessionApi
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
                api_key=self.config.api_key,
                jwt=self.jwt,
            )
        except ApiServerException as e:
            return logger.error(f"Could not create agent - {e}")

        return agent_id

    def patch(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            kwargs["session"] = self
            return func(*args, **kwargs)

        return wrapper

    def _get_response(self) -> Optional[Response]:
        payload = {"session": self.__dict__}
        try:
            response = HttpClient.post(
                f"{self.config.endpoint}/v2/update_session",
                json.dumps(filter_unjsonable(payload)).encode("utf-8"),
                api_key=self.config.api_key,
                jwt=self.jwt,
            )
        except ApiServerException as e:
            return logger.error(f"Could not end session - {e}")

        logger.debug(response.body)
        return response

    def _format_duration(self, start_time, end_time) -> str:
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
        token_cost = response.body.get("token_cost", "unknown")
        if token_cost == "unknown" or token_cost is None:
            return Decimal(0)
        return Decimal(token_cost)

    def _format_token_cost(self, token_cost: Decimal) -> str:
        return (
            "{:.2f}".format(token_cost)
            if token_cost == 0
            else "{:.6f}".format(token_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
        )

    def get_analytics(self) -> Optional[Dict[str, Any]]:
        if not self.end_timestamp:
            self.end_timestamp = get_ISO_time()

        formatted_duration = self._format_duration(self.init_timestamp, self.end_timestamp)

        if (response := self._get_response()) is None:
            return None

        self.token_cost = self._get_token_cost(response)

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
        """Returns the URL for this session in the AgentOps dashboard."""
        assert self.session_id, "Session ID is required to generate a session URL"
        return f"https://app.agentops.ai/drilldown?session_id={self.session_id}"

    # @session_url.setter
    # def session_url(self, url: str):
    #     pass


class SessionsCollection(WeakSet):
    """
    A custom collection for managing Session objects that combines WeakSet's automatic cleanup
    with list-like indexing capabilities.

    This class is needed because:
    1. We want WeakSet's automatic cleanup of unreferenced sessions
    2. We need to access sessions by index (e.g., self._sessions[0]) for backwards compatibility
    3. Standard WeakSet doesn't support indexing
    """

    def __getitem__(self, index: int) -> Session:
        """
        Enable indexing into the collection (e.g., sessions[0]).
        """
        # Convert to list for indexing since sets aren't ordered
        items = list(self)
        return items[index]

    def __iter__(self):
        """
        Override the default iterator to yield sessions sorted by init_timestamp.
        If init_timestamp is not available, fall back to __create_ts.

        WARNING: Using __create_ts as a fallback for ordering may lead to unexpected results
        if init_timestamp is not set correctly.
        """
        return iter(
            sorted(
                super().__iter__(),
                key=lambda session: (
                    session.init_timestamp if hasattr(session, "init_timestamp") else session.__create_ts
                ),
            )
        )


active_sessions: List[Session] = []
