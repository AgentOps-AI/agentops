from __future__ import annotations

import asyncio
import functools
import json
import threading
import traceback
import uuid
import time
from threading import Lock
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Sequence, Union
from uuid import UUID, uuid4
import platform

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
from .enums import EndState, EventType, HttpStatus
from .event import ActionEvent, ErrorEvent, Event, LLMEvent, ToolEvent
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
    """Export OpenTelemetry spans to AgentOps API."""
    def __init__(self, session: "Session", **kwargs):
        """Initialize the exporter with a session."""
        self.session = session
        self._shutdown = threading.Event()
        self._export_lock = threading.Lock()
        super().__init__(**kwargs)

    @property
    def endpoint(self):
        """Get the endpoint URL."""
        return f"{self.session.config.endpoint}/v2/create_events"

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export the spans to AgentOps API."""
        if self._shutdown.is_set():
            return SpanExportResult.SUCCESS

        with self._export_lock:
            try:
                if not spans:
                    return SpanExportResult.SUCCESS

                events = []
                for span in spans:
                    if not span.attributes:
                        logger.warning("Span has no attributes")
                        continue

                    # Ensure required fields are present
                    event_id = span.attributes.get("event.id")
                    if not event_id:
                        event_id = str(uuid.uuid4())
                        logger.debug(f"Generated new event ID: {event_id}")

                    # Get timestamps, ensuring they are always present
                    current_time = datetime.now(timezone.utc).isoformat()
                    init_timestamp = span.attributes.get("event.timestamp")
                    if not init_timestamp:
                        init_timestamp = current_time
                        logger.debug(f"Using current time for init_timestamp: {init_timestamp}")

                    end_timestamp = span.attributes.get("event.end_timestamp")
                    if not end_timestamp:
                        end_timestamp = current_time
                        logger.debug(f"Using current time for end_timestamp: {end_timestamp}")

                    event_data = {
                        "id": event_id,
                        "event_type": span.name,
                        "init_timestamp": init_timestamp,
                        "end_timestamp": end_timestamp,
                        "session_id": str(self.session.session_id),
                    }

                    # Add any additional data from span attributes
                    try:
                        additional_data = json.loads(span.attributes.get("event.data", "{}"))
                        event_data.update(additional_data)
                    except json.JSONDecodeError:
                        logger.error("Failed to decode event data JSON")
                        continue

                    events.append(event_data)

                # Send events to API
                if events:
                    try:
                        response = self.session._get_response(
                            "POST",
                            "/v2/create_events",
                            json={"events": events},
                        )
                        if response.status != HttpStatus.SUCCESS:
                            logger.error(f"Failed to export events: {response.body}")
                            return SpanExportResult.FAILURE
                    except Exception as e:
                        logger.error(f"Error exporting events: {e}")
                        return SpanExportResult.FAILURE

                return SpanExportResult.SUCCESS

            except Exception as e:
                logger.error(f"Error in export: {e}")
                return SpanExportResult.FAILURE

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        """Force flush the exporter."""
        return True

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        self._shutdown.set()

class Session:
    """Main session class for AgentOps."""
    def __init__(
        self,
        session_id: UUID,
        api_key: str,
        tags: Optional[List[str]] = None,
        host_env: Optional[Dict] = None,
        config: Optional[Configuration] = None,
        inherited_session_id: Optional[str] = None,
    ):
        """Initialize a session."""
        self.session_id = session_id
        self.tags = tags or []
        self.host_env = host_env or {}
        self.inherited_session_id = inherited_session_id
        self.init_timestamp = datetime.now(timezone.utc).isoformat()
        self.end_timestamp = None
        self.end_state = None
        self.end_state_reason = None
        self.is_running = False
        self.jwt = None
        self.ended = False
        self.token_cost = Decimal("0")

        # Initialize locks
        self._lock = threading.Lock()
        self._export_lock = threading.Lock()
        self._record_lock = threading.Lock()
        self._end_session_lock = threading.Lock()

        # Initialize configuration
        if config:
            self._config = config
        else:
            self._config = Configuration()
            self._config.api_key = api_key

        # Initialize event counters
        self._llm_calls = 0
        self._tool_calls = 0
        self._action_calls = 0
        self._error_calls = 0
        self.event_counts = {
            "llms": 0,
            "tools": 0,
            "actions": 0,
            "errors": 0
        }

        # Initialize event queue for pre-start events
        self._event_queue = []

        # Set up telemetry
        self._setup_telemetry()

        # Start session if not already started
        if not self.end_timestamp:
            if not self._start_session():
                logger.error("Failed to start session during initialization")
                raise Exception("Failed to start session")

    def end_session(
        self,
        end_state: Optional[Union[EndState, str]] = None,
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None,  # Added to match Client interface
    ) -> Optional[Decimal]:
        """End the session."""
        with self._end_session_lock:
            if not self.is_running or self.ended:
                logger.warning("Session already ended")
                return None

            self.end_timestamp = get_ISO_time()
            self.end_state = end_state or EndState.UNKNOWN
            self.end_state_reason = end_state_reason
            self.ended = True
            self.is_running = False

            # Update session one last time
            self._update_session()

            return self.token_cost

    def add_tags(self, tags: Union[str, List[str]]) -> None:
        """Add tags to the session."""
        if isinstance(tags, str):
            tags = [tags]

        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            logger.warning("Invalid tags format. Tags must be a string or list of strings.")
            return

        # Ensure no duplicates and maintain order
        seen = set()
        self.tags = [tag for tag in self.tags + tags if not (tag in seen or seen.add(tag))]

        # Update session with new tags
        try:
            self._update_session(force_update=True)
        except Exception as e:
            logger.error(f"Failed to update session with new tags: {e}")

    def set_tags(self, tags: Union[str, List[str]]) -> None:
        """Set session tags, replacing any existing tags."""
        if isinstance(tags, str):
            tags = [tags]

        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            logger.warning("Invalid tags format. Tags must be a string or list of strings.")
            return

        self.tags = list(dict.fromkeys(tags))  # Remove duplicates while maintaining order
        try:
            self._update_session(force_update=True)
        except Exception as e:
            logger.error(f"Failed to update session with new tags: {e}")

    def record(self, event: Event) -> None:
        """Record an event."""
        # Queue events if session isn't running yet
        if not self.is_running:
            self._event_queue.append(event)
            return

        # Prepare event data outside the lock
        if not hasattr(event, 'init_timestamp') or event.init_timestamp is None:
            event.init_timestamp = get_ISO_time()
        if not hasattr(event, 'end_timestamp') or event.end_timestamp is None:
            event.end_timestamp = get_ISO_time()

        logger.debug(f"Recording event: type={event.event_type}, class={type(event)}")
        logger.debug(f"Event dict: {event.to_dict()}")

        try:
            # Only lock while updating shared state
            acquired = self._record_lock.acquire(timeout=5)  # 5 second timeout
            if not acquired:
                logger.error("Failed to acquire lock for event recording - possible deadlock")
                return

            try:
                # Update event counts
                if isinstance(event, ActionEvent):
                    self.event_counts["actions"] += 1
                    self._action_calls += 1
                    logger.debug("Counted as ActionEvent")
                elif isinstance(event, ErrorEvent):
                    self.event_counts["errors"] += 1
                    self._error_calls += 1
                    logger.debug("Counted as ErrorEvent")
                elif isinstance(event, LLMEvent):
                    self.event_counts["llms"] += 1
                    self._llm_calls += 1
                    logger.debug("Counted as LLMEvent")
                elif isinstance(event, ToolEvent):
                    self.event_counts["tools"] += 1
                    self._tool_calls += 1
                    logger.debug("Counted as ToolEvent")

                # Send event to server
                self._send_event(event)

                # Update token cost if applicable
                if hasattr(event, "token_cost"):
                    self.token_cost += Decimal(str(event.token_cost))

            finally:
                self._record_lock.release()

        except Exception as e:
            logger.error(f"Error recording event: {e}")
            if isinstance(e, ApiServerException):
                raise

    def _send_event(self, event: Event) -> None:
        """Send an event to the server."""
        try:
            event_data = event.to_dict()
            event_data["session_id"] = str(self.session_id)

            # Ensure required fields are present
            if "init_timestamp" not in event_data:
                event_data["init_timestamp"] = get_ISO_time()
            if "end_timestamp" not in event_data:
                event_data["end_timestamp"] = get_ISO_time()
            if "id" not in event_data:
                event_data["id"] = str(uuid.uuid4())

            response = self._get_response(
                "POST",
                "/v2/create_events",
                json={"events": [event_data]},
            )

            if response.status != HttpStatus.SUCCESS:
                logger.error(f"Failed to send event: {response.body}")
                raise ApiServerException(f"Failed to send event: {response.body}")

        except Exception as e:
            logger.error(f"Error sending event: {e}")
            raise

    def _reauthorize_jwt(self) -> bool:
        """Reauthorize JWT token."""
        try:
            response = self._get_response(
                "POST",
                "/v2/reauthorize_jwt",
                json={"session_id": str(self.session_id)},
            )

            if response.status == HttpStatus.SUCCESS and "jwt" in response.body:
                self.jwt = response.body["jwt"]
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to reauthorize JWT: {e}")
            return False

    def _start_session(self) -> bool:
        """Start a session."""
        if not hasattr(self, '_config') or not self._config or not self._config.api_key:
            logger.error("Could not initialize AgentOps client - API Key is missing or config is invalid.")
            return False

        try:
            # Create session payload with all required data
            payload = {
                "session": {
                    "session_id": str(self.session_id),
                    "init_timestamp": self.init_timestamp,
                    "tags": self.tags,
                    "host_env": self.host_env,
                }
            }

            if hasattr(self, 'inherited_session_id') and self.inherited_session_id:
                payload["session"]["inherited_session_id"] = str(self.inherited_session_id)

            # Single request to create session and get JWT
            response = self._get_response(
                "POST",
                "/v2/create_session",
                json=payload,
            )

            if response.status != HttpStatus.SUCCESS:
                logger.error(f"Failed to start session: {response.body}")
                return False

            # Extract JWT from response
            self.jwt = response.body.get("jwt")
            if not self.jwt:
                logger.error("No JWT in response from create_session")
                return False

            self.is_running = True

            # Initialize event tracking after session is started
            self._initialize_event_tracking()

            # Send any queued events
            if hasattr(self, '_event_queue') and self._event_queue:
                logger.debug(f"Processing {len(self._event_queue)} queued events")
                for event in self._event_queue:
                    self.record(event)
                self._event_queue = []

            return True

        except Exception as e:
            logger.error(f"Error starting session: {e}")
            return False

    def _update_session(self, force_update: bool = False) -> bool:
        """Update session state."""
        if not self.is_running and not force_update:
            return False

        with self._lock:
            try:
                # Prepare session update payload with all required fields
                payload = {
                    "session": {
                        "session_id": str(self.session_id),
                        "init_timestamp": self.init_timestamp,
                        "end_timestamp": self.end_timestamp,
                        "end_state": self.end_state.value if hasattr(self.end_state, 'value') else self.end_state,
                        "end_state_reason": self.end_state_reason,
                        "tags": self.tags,
                        "host_env": self.host_env,
                        "event_counts": self.event_counts,
                        "token_cost": str(self.token_cost) if self.token_cost else "0",
                    }
                }

                # Remove None values
                payload["session"] = {k: v for k, v in payload["session"].items() if v is not None}

                # Use _get_response for consistent header and auth handling
                response = self._get_response(
                    "POST",
                    "/v2/update_session",
                    json=payload
                )

                if response.status != HttpStatus.SUCCESS:
                    logger.error(f"Failed to update session: {response.body}")
                    return False

                # Update token cost if available
                if "token_cost" in response.body:
                    self.token_cost = Decimal(str(response.body["token_cost"]))

                return True

            except Exception as e:
                logger.error(f"Error updating session: {e}")
                return False

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
                jwt=self.jwt if self.jwt else None,
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

            # Update session after successful agent creation
            self._update_session()
            return agent_id
        except ApiServerException as e:
            return logger.error(f"Could not create agent - {e}")

    def patch(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            kwargs["session"] = self
            return func(*args, **kwargs)

        return wrapper

    def _get_response(self, method: str, endpoint: str, **kwargs) -> Response:
        """Make a request to the API."""
        try:
            url = f"{self._config.endpoint}{endpoint}"

            # Extract data from kwargs
            data = kwargs.get("data", "")
            if "json" in kwargs:
                data = json.dumps(kwargs["json"]).encode("utf-8")

            # Extract headers
            headers = kwargs.get("headers", {})

            # Use HttpClient's methods with proper error handling
            if method.upper() == "POST":
                return HttpClient.post(
                    url=url,
                    payload=data,
                    api_key=self._config.api_key,
                    jwt=self.jwt if endpoint != "/v2/create_session" else None,
                    header=headers
                )
            elif method.upper() == "GET":
                return HttpClient.get(
                    url=url,
                    api_key=self._config.api_key,
                    jwt=self.jwt if endpoint != "/v2/create_session" else None,
                    header=headers
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return Response(
                status=500,
                body={"error": str(e)},
                headers={}
            )

    def _format_duration(self, start_time, end_time) -> str:
        """Format duration between two timestamps."""
        try:
            # Convert string timestamps to datetime objects with UTC timezone
            if isinstance(start_time, str):
                start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            else:
                start = start_time.replace(tzinfo=timezone.utc) if start_time.tzinfo is None else start_time

            if isinstance(end_time, str):
                end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            else:
                end = end_time.replace(tzinfo=timezone.utc) if end_time.tzinfo is None else end_time

            # Ensure both timestamps are timezone-aware
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)

            duration = end - start
            return str(int(duration.total_seconds()))
        except Exception as e:
            logger.error(f"Error formatting duration: {e}")
            return "0"

    def _get_token_cost(self, response: Response) -> Decimal:
        """Get token cost from response."""
        try:
            token_cost = response.json().get("token_cost", "unknown")
            return Decimal(token_cost) if token_cost != "unknown" else Decimal("0")
        except (ValueError, AttributeError, KeyError):
            return Decimal("0")

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

        # Update session to get token cost
        self._update_session()

        return {
            "LLM calls": self.event_counts["llms"],
            "Tool calls": self.event_counts["tools"],
            "Actions": self.event_counts["actions"],
            "Errors": self.event_counts["errors"],
            "Duration": formatted_duration,
            "Cost": self._format_token_cost(self.token_cost),
        }

    def _setup_telemetry(self) -> None:
        """Set up OpenTelemetry tracing."""
        # Create a Resource object with service name
        resource = Resource.create({
            SERVICE_NAME: "agentops-sdk",
            "session.id": str(self.session_id),
            "platform.system": platform.system(),
            "platform.release": platform.release(),
        })

        # Create a TracerProvider with the resource
        self._tracer_provider = TracerProvider(resource=resource)

        # Create and register our custom exporter
        self._otel_exporter = SessionExporter(self)
        span_processor = BatchSpanProcessor(self._otel_exporter)
        self._tracer_provider.add_span_processor(span_processor)

        # Set the TracerProvider as the global default
        trace.set_tracer_provider(self._tracer_provider)

        # Get a tracer
        self.tracer = trace.get_tracer(__name__)

    def _initialize_event_tracking(self) -> None:
        """Initialize event tracking."""
        # Initialize event tracking state
        self.event_counts = {
            "llms": 0,
            "tools": 0,
            "actions": 0,
            "errors": 0,
        }
        self.token_cost = Decimal("0")

    @property
    def session_url(self) -> str:
        """Returns the URL for this session in the AgentOps dashboard."""
        assert self.session_id, "Session ID is required to generate a session URL"
        return f"https://app.agentops.ai/drilldown?session_id={self.session_id}"

active_sessions: List[Session] = []
