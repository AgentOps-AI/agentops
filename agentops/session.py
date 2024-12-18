"""Session management for AgentOps.

This module provides session management functionality for the AgentOps SDK.
It includes OpenTelemetry integration for event tracking and monitoring.

OTEL Guidelines:
- Maintain a single TracerProvider for the application runtime
- Have one global TracerProvider in the Client class
- Resource should be initialized once per application and shared across all telemetry
- Each Session gets its own Tracer with session-specific context
- Allow multiple sessions to share the provider while maintaining their own context

Resource Notes:
    Resource represents the entity producing telemetry - in our case, that's the
    AgentOps SDK application itself. Session-specific information should be
    attributes on the spans themselves. A Resource is meant to identify the
    service/process/application, while Sessions are units of work within that
    application.
"""
from __future__ import annotations

import asyncio
import functools
import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Sequence, Union
from uuid import UUID, uuid4

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
from .enums import EndState
from .event import Event, ErrorEvent
from .exceptions import ApiServerException
from .helpers import get_ISO_time, filter_unjsonable, safe_serialize
from .http_client import HttpClient, Response

logger = logging.getLogger(__name__)


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
                        event_id = str(uuid4())

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
                            json_data={"events": events},
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
        session_id: Optional[Union[UUID, str]] = None,
        config: Optional[Configuration] = None,
        tags: Optional[List[str]] = None,
        inherited_session_id: Optional[str] = None,
        auto_start: bool = True,
        video: Optional[str] = None,
        host_env: Optional[dict] = None,
    ):
        """Initialize a new session."""
        self._config = config or Configuration()
        self.session_id = str(session_id) if session_id else str(uuid.uuid4())
        self.inherited_session_id = inherited_session_id
        self.init_timestamp = get_ISO_time()
        self.end_timestamp = None
        self.end_state: Optional[str] = "Indeterminate"
        self.end_state_reason: Optional[str] = None
        self.is_running = False
        self.tags: List[str] = tags or []
        self.video: Optional[str] = video
        self.host_env = host_env
        self.jwt = None
        self._session_url = ""
        self.token_cost: Decimal = Decimal(0)
        self._lock = threading.Lock()
        self._end_session_lock = threading.Lock()
        self.event_counts = {
            "llms": 0,
            "tools": 0,
            "actions": 0,
            "errors": 0,
            "apis": 0,
        }

        # Initialize OTEL components
        self._tracer_provider = TracerProvider()
        self._otel_tracer = self._tracer_provider.get_tracer(
            f"agentops.session.{self.session_id}",
        )
        self._otel_exporter = SessionExporter(session=self)

        # Configure span processor
        self._span_processor = BatchSpanProcessor(
            self._otel_exporter,
            max_queue_size=self._config.max_queue_size,
            schedule_delay_millis=self._config.max_wait_time,
            max_export_batch_size=min(
                max(self._config.max_queue_size // 20, 1),
                min(self._config.max_queue_size, 32),
            ),
            export_timeout_millis=20000,
        )
        self._tracer_provider.add_span_processor(self._span_processor)

        if auto_start and self._config.auto_start_session:
            self._start_session()

    def end_session(
        self,
        end_state: str = "Success",
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None,
    ) -> Union[Decimal, None]:
        """End the session and return the total token cost.

        Args:
            end_state (str, optional): The final state. Defaults to "Success".
            end_state_reason (str, optional): Reason for ending. Defaults to None.
            video (str, optional): URL to session recording. Defaults to None.

        Returns:
            Union[Decimal, None]: Total token cost or None if session not running.
        """
        with self._end_session_lock:
            if not self.is_running:
                return None

            if not any(end_state == state.value for state in EndState):
                logger.warning("Invalid end_state. Please use one of the EndState enums")
                return None

            try:
                # Force flush any pending spans before ending session
                if hasattr(self, "_span_processor"):
                    self._span_processor.force_flush(timeout_millis=5000)

                # 1. Set shutdown flag on exporter first
                if hasattr(self, "_otel_exporter"):
                    self._otel_exporter.shutdown()

                # 2. Set session end state
                self.end_timestamp = get_ISO_time()
                self.end_state = end_state
                self.end_state_reason = end_state_reason
                if video is not None:
                    self.video = video

                # 3. Mark session as not running before cleanup
                self.is_running = False

                # 4. Clean up OTEL components
                if hasattr(self, "_span_processor"):
                    try:
                        # Force flush any pending spans
                        self._span_processor.force_flush(timeout_millis=5000)
                        # Shutdown the processor
                        self._span_processor.shutdown()
                    except Exception as e:
                        logger.warning(f"Error during span processor cleanup: {e}")
                    finally:
                        del self._span_processor

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

    def add_tags(self, tags: Union[str, List[str]]) -> None:
        """Add tags to the session.

        Args:
            tags (Union[str, List[str]]): A string or list of strings to add as tags.
        """
        if isinstance(tags, str):
            new_tags = [tags]
        elif isinstance(tags, (list, tuple)):
            new_tags = [str(tag) for tag in tags]  # Ensure all tags are strings
        else:
            raise ValueError("Tags must be a string or list of strings")

        self.tags.extend(new_tags)
        self.tags = list(set(self.tags))  # Remove duplicates

        if self.is_running:
            self._update_session()

    def set_tags(self, tags: Union[str, List[str]]) -> None:
        """
        Replace session tags at runtime.
        """
        if isinstance(tags, str):
            self.tags = [tags]
        elif isinstance(tags, (list, tuple)):
            self.tags = [str(tag) for tag in tags]  # Ensure all tags are strings
        else:
            raise ValueError("Tags must be a string or list of strings")

        self.tags = list(set(self.tags))  # Remove duplicates
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

        # Create session context
        token = set_value("session.id", str(self.session_id))

        try:
            token = attach(token)

            # Create a copy of event data to modify
            event_data = dict(filter_unjsonable(event.__dict__))

            # Add required fields based on event type
            if isinstance(event, ErrorEvent):
                event_data["error_type"] = getattr(event, "error_type", event.event_type)
            elif event.event_type == "actions":
                # Ensure action events have action_type
                if "action_type" not in event_data:
                    event_data["action_type"] = event_data.get("name", "unknown_action")
                if "name" not in event_data:
                    event_data["name"] = event_data.get("action_type", "unknown_action")
            elif event.event_type == "tools":
                # Ensure tool events have name
                if "name" not in event_data:
                    event_data["name"] = event_data.get("tool_name", "unknown_tool")
                if "tool_name" not in event_data:
                    event_data["tool_name"] = event_data.get("name", "unknown_tool")

            with self._otel_tracer.start_as_current_span(
                name=event.event_type,
                attributes={
                    "event.id": str(event.id),
                    "event.type": event.event_type,
                    "event.timestamp": event.init_timestamp or get_ISO_time(),
                    "event.end_timestamp": event.end_timestamp or get_ISO_time(),
                    "session.id": str(self.session_id),
                    "session.tags": ",".join(self.tags) if self.tags else "",
                    "event.data": json.dumps(event_data),
                },
            ) as span:
                if event.event_type in self.event_counts:
                    self.event_counts[event.event_type] += 1

                if isinstance(event, ErrorEvent):
                    span.set_attribute("error", True)
                    if hasattr(event, "trigger_event") and event.trigger_event:
                        span.set_attribute("trigger_event.id", str(event.trigger_event.id))
                        span.set_attribute("trigger_event.type", event.trigger_event.event_type)

                if flush_now and hasattr(self, "_span_processor"):
                    self._span_processor.force_flush()
        finally:
            detach(token)

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
                json_data=payload,
                jwt=self.jwt,
            )
        except Exception as e:
            logger.error(f"Failed to send event: {e}")

    def _reauthorize_jwt(self) -> Union[str, None]:
        with self._lock:
            payload = {"session_id": self.session_id}
            res = HttpClient.post(
                f"{self.config.endpoint}/v2/reauthorize_jwt",
                json_data=payload,
                api_key=self.config.api_key,
            )

            logger.debug(res.body)

            if res.code != 200:
                return None

            jwt = res.body.get("jwt", None)
            self.jwt = jwt
            return jwt

    def _start_session(self) -> None:
        """Start a new session."""
        if not self._config.api_key:
            raise ValueError("API key is required to start a session")

        if self.is_running:
            return

        self.start_time = datetime.now(timezone.utc)
        self.is_running = True

        response = HttpClient.post(
            "/v2/start_session",
            json_data={
                "session": {
                    "session_id": str(self.session_id),
                    "tags": self.tags or [],
                    "inherited_session_id": self.inherited_session_id,
                    "start_time": get_ISO_time(),
                }
            },
            api_key=self._config.api_key,
        )

        if response.status == "success":
            self.jwt = response.body.get("jwt")
            self.session_url = response.body.get("session_url")
            print(f"🖇 AgentOps: Session Replay: {self.session_url}")

    def _update_session(self) -> None:
        """Update session state on the server"""
        if not self.is_running:
            return
        with self._lock:  # TODO: Determine whether we really need to lock here: are incoming calls coming from other threads?
            payload = {"session": self.__dict__}

            try:
                res = HttpClient.post(
                    f"{self.config.endpoint}/v2/update_session",
                    json_data=filter_unjsonable(payload),
                    api_key=self.config.api_key,
                    jwt=self.jwt,
                )
                if res.code != 200:
                    return logger.error(f"Could not update session - server returned {res.code}")
                return True
            except ApiServerException as e:
                return logger.error(f"Could not update session - {e}")
            except Exception as e:
                return logger.error(f"Unexpected error updating session - {e}")

    def create_agent(self, name, agent_id):
        if not self.is_running:
            return
        if agent_id is None:
            agent_id = str(uuid4())

        payload = {
            "id": agent_id,
            "name": name,
        }

        try:
            HttpClient.post(
                f"{self.config.endpoint}/v2/create_agent",
                json_data=payload,
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
                json_data=filter_unjsonable(payload),
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

    @property
    def jwt_token(self) -> Optional[str]:
        """Get the JWT token for this session."""
        return self.jwt

    # @session_url.setter
    # def session_url(self, url: str):
    #     pass


active_sessions: List[Session] = []
