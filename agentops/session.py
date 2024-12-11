from __future__ import annotations

import asyncio
import functools
import json
import threading
import traceback
import uuid
from threading import Lock
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Sequence, Union

import requests
from opentelemetry import trace
from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
    SpanExportResult,
)
from termcolor import colored

from .config import Configuration
from .enums import EndState, EventType
from .event import ActionEvent, ErrorEvent, Event
from .exceptions import ApiServerException
from .helpers import filter_unjsonable, get_ISO_time, safe_serialize
from .http_client import HttpClient, Response
from .log_config import logger

"""
OTEL Guidelines:



- Maintain a single TracerProvider for the application runtime
    - Have one global TracerProvider in the Client class

- According to the OpenTelemetry Python documentation, Resource should be initialized once per application and shared across all telemetry (traces, metrics, logs).
- Each Session gets its own Tracer (with session-specific context)
- Allow multiple sessions to share the provider while maintaining their own context



:: Resource

    ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
    Captures information about the entity producing telemetry as Attributes.
    For example, a process producing telemetry that is running in a container
    on Kubernetes has a process name, a pod name, a namespace, and possibly
    a deployment name. All these attributes can be included in the Resource.
    ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    The key insight from the documentation is:

    - Resource represents the entity producing telemetry - in our case, that's the AgentOps SDK application itself
    - Session-specific information should be attributes on the spans themselves
        - A Resource is meant to identify the service/process/application1
        - Sessions are units of work within that application
        - The documentation example about "process name, pod name, namespace" refers to where the code is running, not the work it's doing

"""


class SessionExporter(SpanExporter):
    """
    Manages publishing events for Session
    """

    def __init__(self, session: Session, **kwargs):
        self.session = session
        self._shutdown = threading.Event()
        self._export_lock = threading.Lock()
        super().__init__(**kwargs)

    @property
    def endpoint(self):
        return f"{self.session.config.endpoint}/v2/create_events"

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._shutdown.is_set():
            return SpanExportResult.SUCCESS

        with self._export_lock:
            try:
                # Skip if no spans to export
                if not spans:
                    return SpanExportResult.SUCCESS

                events = []
                for span in spans:
                    event_data = json.loads(span.attributes.get("event.data", "{}"))

                    # Format event data based on event type
                    if span.name == "actions":
                        formatted_data = {
                            "action_type": event_data.get("action_type", event_data.get("name", "unknown_action")),
                            "params": event_data.get("params", {}),
                            "returns": event_data.get("returns"),
                        }
                    elif span.name == "tools":
                        formatted_data = {
                            "name": event_data.get("name", event_data.get("tool_name", "unknown_tool")),
                            "params": event_data.get("params", {}),
                            "returns": event_data.get("returns"),
                        }
                    else:
                        formatted_data = event_data

                    formatted_data = {**event_data, **formatted_data}
                    # Get timestamps, providing defaults if missing
                    current_time = datetime.now(timezone.utc).isoformat()
                    init_timestamp = span.attributes.get("event.timestamp")
                    end_timestamp = span.attributes.get("event.end_timestamp")

                    # Handle missing timestamps
                    if init_timestamp is None:
                        init_timestamp = current_time
                    if end_timestamp is None:
                        end_timestamp = current_time

                    # Get event ID, generate new one if missing
                    event_id = span.attributes.get("event.id")
                    if event_id is None:
                        event_id = str(uuid.uuid4())

                    events.append(
                        {
                            "id": event_id,
                            "event_type": span.name,
                            "init_timestamp": init_timestamp,
                            "end_timestamp": end_timestamp,
                            **formatted_data,
                            "session_id": str(self.session.session_id),
                        }
                    )

                # Only make HTTP request if we have events and not shutdown
                if events:
                    try:
                        res = HttpClient.post(
                            self.endpoint,
                            json.dumps({"events": events}).encode("utf-8"),
                            api_key=self.session.config.api_key,
                            jwt=self.session.jwt,
                        )
                        return SpanExportResult.SUCCESS if res.code == 200 else SpanExportResult.FAILURE
                    except Exception as e:
                        logger.error(f"Failed to send events: {e}")
                        return SpanExportResult.FAILURE

                return SpanExportResult.SUCCESS

            except Exception as e:
                logger.error(f"Failed to export spans: {e}")
                return SpanExportResult.FAILURE

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        return True

    def shutdown(self) -> None:
        """Handle shutdown gracefully"""
        self._shutdown.set()
        # Don't call session.end_session() here to avoid circular dependencies


class Session:
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
        api_key: str,
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        host_env: Optional[Dict] = None,
        config: Optional[Configuration] = None,
    ):
        """Initialize Session."""
        self.api_key = api_key
        self.session_id = session_id or str(uuid.uuid4())
        self.tags = tags or []
        self.host_env = host_env
        self.config = config or Configuration()
        self.jwt = None
        self.init_timestamp = datetime.utcnow().isoformat()
        self.end_timestamp = None
        self.end_state = None
        self.end_state_reason = None
        self.video = None
        self.ended = False
        self.is_running = False
        self.token_cost = Decimal("0")
        self.event_counts = {
            "llms": 0,
            "tools": 0,
            "actions": 0,
            "apis": 0,
            "errors": 0,
        }

        # Initialize locks
        self._end_session_lock = Lock()
        self._update_session_lock = Lock()
        self._record_lock = Lock()

        # Initialize tracing
        self._tracer_provider = TracerProvider()
        self._exporter = SessionExporter(self)
        self._span_processor = BatchSpanProcessor(self._exporter)
        self._tracer_provider.add_span_processor(self._span_processor)
        self._tracer = self._tracer_provider.get_tracer(__name__)
        self._otel_tracer = self._tracer
        self._otel_exporter = self._exporter

        # Start session
        if self._start_session():
            self.is_running = True

    def end_session(
        self,
        end_state: Optional[str] = None,
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None,
        force: bool = False,
    ) -> None:
        """End session and send final update to AgentOps API."""
        if self.ended and not force:
            logger.warning("Session already ended")
            return

        try:
            self.end_state = end_state or "Success"  # Default to Success if not provided
            self.end_state_reason = end_state_reason
            self.video = video
            self.end_timestamp = datetime.utcnow().isoformat()

            # Update session first to get the response
            self._update_session()
            analytics_stats = self.get_analytics()
            if not analytics_stats:
                logger.warning("Could not get analytics stats")

            self.ended = True

        except Exception as e:
            logger.error(f"Error during session end: {str(e)}")
            traceback.print_exc()

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

    def record(self, event: Union[Event, ErrorEvent]) -> None:
        """
        Record an event with the AgentOps service.

        Args:
            event (Event): The event to record.
        """
        if not self.is_running:
            return

        # Ensure event has timestamps
        if event.init_timestamp is None:
            event.init_timestamp = get_ISO_time()
        if event.end_timestamp is None:
            event.end_timestamp = get_ISO_time()

        # Update event counts
        if isinstance(event, ErrorEvent):
            self.event_counts["errors"] += 1
        elif event.event_type == EventType.LLM:
            self.event_counts["llms"] += 1
        elif event.event_type == EventType.TOOL:
            self.event_counts["tools"] += 1
        elif event.event_type == EventType.ACTION:
            self.event_counts["actions"] += 1
        elif event.event_type == EventType.API:
            self.event_counts["apis"] += 1

        # Create span for event
        with self._otel_tracer.start_as_current_span(
            event.event_type,
            attributes={
                "event.id": str(event.id),
                "event.data": safe_serialize(event.to_dict()),
                "event.timestamp": event.init_timestamp,
                "event.end_timestamp": event.end_timestamp,
            },
        ) as span:
            # Let the span end naturally when the context exits
            pass

        # Update token cost if applicable
        if hasattr(event, "token_cost"):
            self.token_cost += Decimal(str(event.token_cost))

        # Don't update session for every event to reduce requests
        if event.event_type != EventType.ACTION or event.action_type != "create_agent":
            self._update_session()

    def _send_event(self, event: Union[Event, ErrorEvent]) -> None:
        """Send event to AgentOps API."""
        headers = {
            "Content-Type": "application/json",
            "X-Agentops-Api-Key": self.api_key,
            "Authorization": f"Bearer {self.jwt}",
        }
        self._get_response("POST", "/v2/create_events", headers=headers, json={"events": [event.to_dict()]})

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

    def _start_session(self) -> bool:
        """Start session with AgentOps API."""
        if not self.api_key:
            logger.error("Could not start session - API Key is missing")
            return False

        headers = {
            "Content-Type": "application/json",
            "X-Agentops-Api-Key": self.api_key,
        }

        response = self._get_response(
            "POST",
            "/v2/create_session",
            headers=headers,
            json={
                "session_id": str(self.session_id),
                "tags": self.tags,
                "host_env": self.host_env,
            },
        )

        if not response.ok:
            return False

        data = response.json()
        if "jwt" not in data:
            return False

        self.jwt = data["jwt"]
        return True

    def _update_session(self, force: bool = False) -> None:
        """Update session with AgentOps API."""
        if not self.api_key:
            logger.error("Could not update session - API Key is missing")
            return

        headers = {
            "Content-Type": "application/json",
            "X-Agentops-Api-Key": self.api_key,
        }
        if self.jwt:
            headers["Authorization"] = f"Bearer {self.jwt}"

        data = {
            "session_id": str(self.session_id),
            "end_state": self.end_state,
            "end_state_reason": self.end_state_reason,
            "video": self.video,
            "end_timestamp": self.end_timestamp,
        }

        response = self._get_response(
            "POST",
            "/v2/update_session",
            headers=headers,
            json=data,
        )

        if not response.ok:
            logger.error(f"Failed to update session: {response.text}")

    def create_agent(self, name, agent_id=None, skip_event=False):
        """
        Create an agent and optionally record the creation event.

        Args:
            name (str): Name of the agent
            agent_id (str, optional): Unique identifier for the agent. Generated if not provided.
            skip_event (bool, optional): If True, skip event recording but still create agent.

        Returns:
            str: The agent ID if successful, None otherwise
        """
        if not self.is_running:
            return
        if agent_id is None:
            agent_id = str(uuid.uuid4())

        # Create the agent in the API regardless of skip_event
        payload = {
            "id": agent_id,
            "name": name,
            "session_id": str(self.session_id),
        }

        try:
            res = HttpClient.post(
                f"{self.config.endpoint}/v2/create_agent",
                json.dumps(payload).encode("utf-8"),
                api_key=self.config.api_key,
                jwt=self.jwt,
            )

            # Only record the event if skip_event is False
            if not skip_event:
                event = Event(
                    event_type=EventType.CREATE_AGENT,
                    agent_id=agent_id,
                    agent_name=name,
                    session_id=str(self.session_id),
                    timestamp=get_ISO_time(),
                )
                self.record(event)

            return agent_id
        except ApiServerException as e:
            return logger.error(f"Could not create agent - {e}")

    def patch(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            kwargs["session"] = self
            return func(*args, **kwargs)

        return wrapper

    def _get_response(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to AgentOps API."""
        url = f"{self.config.endpoint}{endpoint}"

        # Initialize base headers
        base_headers = {"X-AgentOps-Api-Key": self.api_key}
        if self.jwt:
            base_headers["Authorization"] = f"Bearer {self.jwt}"

        # Merge with provided headers if any
        if "headers" in kwargs:
            headers = {**base_headers, **kwargs["headers"]}
            kwargs["headers"] = headers
        else:
            kwargs["headers"] = base_headers

        response = requests.request(method, url, **kwargs)
        if response.status_code == 401:
            self._reauthorize_jwt()
            kwargs["headers"]["Authorization"] = f"Bearer {self.jwt}"
            response = requests.request(method, url, **kwargs)
        return response

    def _format_duration(self, start_time, end_time) -> str:
        """Format duration between two timestamps."""
        try:
            # Handle both datetime objects and ISO format strings
            if isinstance(start_time, str):
                start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            else:
                start = start_time

            if isinstance(end_time, str):
                end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            else:
                end = end_time

            duration = end - start
            return str(int(duration.total_seconds()))
        except Exception as e:
            logger.error(f"Error formatting duration: {e}")
            return "0"

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
        """Get analytics data for the session."""
        if not self.end_timestamp:
            self.end_timestamp = get_ISO_time()

        formatted_duration = self._format_duration(self.init_timestamp, self.end_timestamp)

        # No need to make another update_session request here
        # Just return the analytics data
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


active_sessions: List[Session] = []
