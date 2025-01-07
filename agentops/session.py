from __future__ import annotations

import asyncio
import functools
import json
import threading
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Sequence, Union
from uuid import UUID, uuid4

from opentelemetry import trace
from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from termcolor import colored

from .config import Configuration
from .enums import EndState
from .event import ActionEvent, ErrorEvent, Event, LLMEvent, ToolEvent
from .exceptions import ApiServerException
from .helpers import filter_unjsonable, get_ISO_time, safe_serialize
from .http_client import HttpClient, Response
from .log_config import logger
from .telemetry.client import ClientTelemetry
from .telemetry.converter import AgentOpsAttributes, EventToSpanConverter

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
        client (ClientTelemetry): The client telemetry object for the session.
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
        client: Optional[ClientTelemetry] = None,
        tags: Optional[List[str]] = None,
        host_env: Optional[dict] = None,
    ):
        """Initialize session with telemetry handled by ClientTelemetry"""
        self.session_id = session_id
        self.config = config
        self.tags = tags or []
        self.init_timestamp = get_ISO_time()
        self.end_timestamp = None
        self.end_state = EndState.INDETERMINATE.value
        self.end_state_reason = None
        self.token_cost = Decimal(0)
        self.event_counts = {
            "llms": 0,
            "tools": 0,
            "actions": 0,
            "errors": 0,
            "apis": 0,
        }
        self._lock = threading.Lock()
        self._end_session_lock = threading.Lock()
        self.is_running = True
        self.jwt = None

        # Start session first to get JWT
        if not self._start_session():
            raise Exception("Failed to start session")

        # Get session-specific tracer from client telemetry
        from agentops.client import Client
        self._telemetry_client = client or Client()._telemetry
        
        # Get tracer from client
        self._otel_tracer = self._telemetry_client.get_session_tracer(
            session_id=self.session_id,
            config=self.config,
            jwt=self.jwt or ""
        )

        # For test compatibility
        self._tracer_provider = self._telemetry_client._tracer_provider
        # Use existing span processor from client
        self._span_processor = self._telemetry_client._session_exporters[self.session_id]

    def set_video(self, video: str) -> None:
        """
        Sets a url to the video recording of the session.

        Args:
            video (str): The url of the video recording
        """
        self.video = video

    def _flush_spans(self) -> bool:
        """
        Flush pending spans for this specific session with timeout.
        Returns True if flush was successful, False otherwise.
        """
        if not hasattr(self, "_span_processor"):
            return True

        try:
            success = self._span_processor.force_flush(timeout_millis=self.config.max_wait_time)
            if not success:
                logger.warning("Failed to flush all spans before session end")
            return success
        except Exception as e:
            logger.warning(f"Error flushing spans: {e}")
            return False

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
                # Force flush any pending spans
                if self._telemetry_client:
                    self._telemetry_client.force_flush()

                # Set session end state
                self.end_timestamp = get_ISO_time()
                self.end_state = end_state
                self.end_state_reason = end_state_reason
                if video is not None:
                    self.video = video

                # Mark session as not running
                self.is_running = False

                # Get analytics before cleanup
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

                # Clean up telemetry
                if self._telemetry_client:
                    self._telemetry_client.cleanup_session(self.session_id)

                return self.token_cost

            except Exception as e:
                logger.exception(f"Error during session end: {e}")
                return None
            finally:
                active_sessions.remove(self)
                logger.info(
                    colored(
                        f"\x1b[34mSession Replay: {self.session_url}\x1b[0m",
                        "blue",
                    )
                )

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

        # Set session_id on the event itself
        event.session_id = self.session_id

        # Create session context
        token = set_value("session.id", str(self.session_id))

        try:
            token = attach(token)
            
            # Get span definitions from converter
            span_definitions = EventToSpanConverter.convert_event(event)
            
            # Create spans based on definitions
            for span_def in span_definitions:
                # Add session context to span attributes
                span_def.attributes.update({
                    AgentOpsAttributes.SESSION_ID: str(self.session_id),
                    AgentOpsAttributes.SESSION_TAGS: ",".join(self.tags) if self.tags else "",
                    # Add session_id to event data
                    AgentOpsAttributes.EVENT_DATA: json.dumps({
                        "session_id": str(self.session_id),
                        **span_def.attributes.get(AgentOpsAttributes.EVENT_DATA, {})
                    })
                })
                
                with self._otel_tracer.start_as_current_span(
                    name=span_def.name,
                    attributes=span_def.attributes,
                    kind=span_def.kind or trace.SpanKind.INTERNAL
                ) as span:
                    if event.event_type in self.event_counts:
                        self.event_counts[event.event_type] += 1

                    if flush_now:
                        self._telemetry_client.force_flush()
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
        if not self.is_running:
            return

        # TODO: Determine whether we really need to lock here: are incoming calls coming from other threads?
        with self._lock:
            payload = {"session": self.__dict__}

            try:
                res = HttpClient.post(
                    f"{self.config.endpoint}/v2/update_session",
                    json.dumps(filter_unjsonable(payload)).encode("utf-8"),
                    # self.config.api_key,
                    jwt=self.jwt,
                )
            except ApiServerException as e:
                return logger.error(f"Could not update session - {e}")

    def create_agent(self, name, agent_id):
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

    def _format_event_data(self, event: Union[Event, ErrorEvent]) -> Dict[str, Any]:
        """
        Format event data for telemetry export.
        Extracts relevant fields from event and ensures they're JSON-serializable.
        """
        # Get base event fields from Event class
        event_data = {
            "event_type": event.event_type,
            "params": event.params,
            "returns": event.returns,
            "init_timestamp": event.init_timestamp,
            "end_timestamp": event.end_timestamp,
        }

        # Add event-type specific fields
        if isinstance(event, ErrorEvent):
            event_data.update({
                "error_type": event.error_type,
                "code": event.code,
                "details": event.details,
                "logs": event.logs,
            })
        elif isinstance(event, ActionEvent):
            event_data.update({
                "action_type": event.action_type,
                "logs": event.logs,
                "screenshot": event.screenshot,
            })
        elif isinstance(event, ToolEvent):
            event_data.update({
                "name": event.name,
                "logs": event.logs,
            })
        elif isinstance(event, LLMEvent):
            event_data.update({
                "model": event.model,
                "prompt": event.prompt,
                "completion": event.completion,
                "prompt_tokens": event.prompt_tokens,
                "completion_tokens": event.completion_tokens,
            })

        # Filter out None values and ensure JSON-serializable
        return {k: v for k, v in filter_unjsonable(event_data).items() if v is not None}


active_sessions: List[Session] = []
