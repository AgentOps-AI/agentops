from __future__ import annotations

import asyncio
import functools
import json
import threading
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional, Sequence, Union
from uuid import UUID, uuid4

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter, SpanExportResult
from termcolor import colored

from .config import Configuration
from .enums import EndState
from .event import ErrorEvent, Event
from .exceptions import ApiServerException
from .helpers import filter_unjsonable, get_ISO_time, safe_serialize
from .http_client import HttpClient
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

    _tracer_provider = None

    @staticmethod
    def get_tracer_provider():
        """Get or create the global tracer provider"""
        if SessionExporter._tracer_provider is None:
            # Initialize with default resource
            resource = Resource.create(
                {
                    "service.name": "agentops",
                    # Additional resource attributes can be added here
                }
            )
            SessionExporter._tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(SessionExporter._tracer_provider)
        return SessionExporter._tracer_provider

    def __init__(self, session: Session, **kwargs):
        self.session = session
        super().__init__(**kwargs)

    @property
    def headers(self):
        # Using a computed @property as session.jwt might change
        return {"Authorization": f"Bearer {self.session.jwt}", "Content-Type": "application/json"}

    @property
    def endpoint(self):
        return f"{self.session.config.endpoint}/v2/create_events"

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            events = []
            for span in spans:
                # Convert span to AgentOps event format
                assert hasattr(span, "attributes")
                events.append(
                    {
                        "id": span.attributes.get("event.id"),
                        "event_type": span.name,
                        "init_timestamp": span.attributes.get("event.timestamp"),
                        "end_timestamp": span.attributes.get("event.end_timestamp"),
                        "data": span.attributes.get("event.data", {}),
                    }
                )

            if events:
                # Use existing HttpClient to send events
                res = HttpClient.post(
                    self.endpoint,
                    json.dumps({"events": events}).encode("utf-8"),
                    self.session.config.api_key,
                    header=self.headers,
                )
                if res.code == 200:
                    return SpanExportResult.SUCCESS

            return SpanExportResult.FAILURE
        except Exception as e:
            logger.error(f"Failed to export spans: {e}")
            return SpanExportResult.FAILURE

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        return True

    def shutdown(self) -> None:
        self.session.end_session()


class Session:
    """
    Represents a session of events, with a start and end state.

    Args:
        session_id (UUID): The session id is used to record particular runs.
        tags (List[str], optional): Tags that can be used for grouping or sorting later. Examples could be ["GPT-4"].

    Attributes:
        init_timestamp (float): The timestamp for when the session started, represented as seconds since the epoch.
        end_timestamp (float, optional): The timestamp for when the session ended, represented as seconds since the epoch. This is only set after end_session is called.
        end_state (str, optional): The final state of the session. Suggested: "Success", "Fail", "Indeterminate". Defaults to "Indeterminate".
        end_state_reason (str, optional): The reason for ending the session.

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
        self.event_counts = {
            "llms": 0,
            "tools": 0,
            "actions": 0,
            "errors": 0,
            "apis": 0,
        }

        # Get tracer from global provider with session-specific context
        self._otel_tracer = trace.get_tracer(
            f"agentops.session.{str(session_id)}",  # Include session ID for unique identification
            schema_url="https://opentelemetry.io/schemas/1.11.0",
        )

        # Start session first to get JWT
        self.is_running = self._start_session()
        if not self.is_running:
            return

        # Configure custom AgentOps exporter
        self._otel_exporter = SessionExporter(session=self)

        # Add session-specific processor to the global provider
        span_processor = BatchSpanProcessor(
            self._otel_exporter,
            max_queue_size=self.config.max_queue_size,
            schedule_delay_millis=self.config.max_wait_time,
            max_export_batch_size=self.config.max_queue_size,
        )

        SessionExporter.get_tracer_provider().add_span_processor(span_processor)

    def set_video(self, video: str) -> None:
        """
        Sets a url to the video recording of the session.

        Args:
            video (str): The url of the video recording
        """
        self.video = video

    def _flush_spans(self) -> bool:
        """
        Flush all pending spans with timeout.
        Returns True if flush was successful, False otherwise.
        """
        if not hasattr(self, "_tracer"):
            return True

        success = True
        for processor in SessionExporter.get_tracer_provider().span_processors:
            if not processor.force_flush(timeout_millis=self.config.max_wait_time):
                logger.warning("Failed to flush all spans before session end")
                success = False
        return success

    def end_session(
        self,
        end_state: str = "Indeterminate",
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None,
    ) -> Union[Decimal, None]:
        if not self.is_running:
            return None

        if not any(end_state == state.value for state in EndState):
            return logger.warning("Invalid end_state. Please use one of the EndState enums")

        self.end_timestamp = get_ISO_time()
        self.end_state = end_state
        self.end_state_reason = end_state_reason
        if video is not None:
            self.video = video

        # Shutdown sequence
        try:
            # 1. Stop accepting new spans
            self.is_running = False

            # 2. Flush all pending spans
            self._flush_spans()

        except Exception as e:
            logger.warning(f"Error during OpenTelemetry shutdown: {e}")

        # Update session state
        with self._lock:
            payload = {"session": self.__dict__}
            try:
                res = HttpClient.post(
                    f"{self.config.endpoint}/v2/update_session",
                    json.dumps(filter_unjsonable(payload)).encode("utf-8"),
                    jwt=self.jwt,
                )
            except ApiServerException as e:
                return logger.error(f"Could not end session - {e}")

        logger.debug(res.body)
        token_cost = res.body.get("token_cost", "unknown")

        def format_duration(start_time, end_time):
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

        formatted_duration = format_duration(self.init_timestamp, self.end_timestamp)

        if token_cost == "unknown" or token_cost is None:
            token_cost_d = Decimal(0)
        else:
            token_cost_d = Decimal(token_cost)

        formatted_cost = (
            "{:.2f}".format(token_cost_d)
            if token_cost_d == 0
            else "{:.6f}".format(token_cost_d.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
        )

        analytics = (
            f"Session Stats - "
            f"{colored('Duration:', attrs=['bold'])} {formatted_duration} | "
            f"{colored('Cost:', attrs=['bold'])} ${formatted_cost} | "
            f"{colored('LLMs:', attrs=['bold'])} {self.event_counts['llms']} | "
            f"{colored('Tools:', attrs=['bold'])} {self.event_counts['tools']} | "
            f"{colored('Actions:', attrs=['bold'])} {self.event_counts['actions']} | "
            f"{colored('Errors:', attrs=['bold'])} {self.event_counts['errors']}"
        )
        logger.info(analytics)

        session_url = res.body.get(
            "session_url",
            f"https://app.agentops.ai/drilldown?session_id={self.session_id}",
        )

        logger.info(
            colored(
                f"\x1b[34mSession Replay: {session_url}\x1b[0m",
                "blue",
            )
        )

        active_sessions.remove(self)

        return token_cost_d

    def add_tags(self, tags: List[str]) -> None:
        """
        Append to session tags at runtime.

        Args:
            tags (List[str]): The list of tags to append.
        """
        if not self.is_running:
            return

        if not (isinstance(tags, list) and all(isinstance(item, str) for item in tags)):
            if isinstance(tags, str):
                tags = [tags]

        if self.tags is None:
            self.tags = tags
        else:
            for tag in tags:
                if tag not in self.tags:
                    self.tags.append(tag)

        self._update_session()

    def set_tags(self, tags):
        if not self.is_running:
            return

        if not (isinstance(tags, list) and all(isinstance(item, str) for item in tags)):
            if isinstance(tags, str):
                tags = [tags]

        self.tags = tags
        self._update_session()

    def record(self, event: Union[Event, ErrorEvent]):
        """Record an event using OpenTelemetry spans"""
        if not self.is_running:
            return

        # Use session-specific tracer with session context
        with self._otel_tracer.start_as_current_span(
            name=event.event_type,
            attributes={
                "event.id": str(event.id),
                "event.type": event.event_type,
                "event.timestamp": event.init_timestamp,
                "session.id": str(self.session_id),
                "session.tags": ",".join(self.tags) if self.tags else "",
                "event.data": json.dumps(filter_unjsonable(event.__dict__)),
            },
        ) as span:
            # Update event counts
            if event.event_type in self.event_counts:
                self.event_counts[event.event_type] += 1

            if isinstance(event, ErrorEvent):
                span.set_attribute("error", True)
                if event.trigger_event:
                    span.set_attribute("trigger_event.id", str(event.trigger_event.id))
                    span.set_attribute("trigger_event.type", event.trigger_event.event_type)

            # Set end time if not already set
            if not event.end_timestamp:
                event.end_timestamp = get_ISO_time()
                span.set_attribute("event.end_timestamp", event.end_timestamp)

            # Force flush to ensure events are sent immediately in tests
            if getattr(self.config, "testing", False):
                for processor in SessionExporter.get_tracer_provider().span_processors:
                    processor.force_flush()

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
        """Initialize session and get JWT token"""
        payload = {"session": self.__dict__}
        try:
            res = HttpClient.post(
                f"{self.config.endpoint}/v2/create_session",
                json.dumps(filter_unjsonable(payload)).encode("utf-8"),
                self.config.api_key,
                self.config.parent_key,
            )
        except ApiServerException as e:
            return logger.error(f"Could not start session - {e}")

        if res.code != 200:
            return False

        self.jwt = res.body.get("jwt")
        return bool(self.jwt)

    def _update_session(self) -> None:
        if not self.is_running:
            return
        with self._lock:
            payload = {"session": self.__dict__}

            try:
                res = HttpClient.post(
                    f"{self.config.endpoint}/v2/update_session",
                    json.dumps(filter_unjsonable(payload)).encode("utf-8"),
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


active_sessions: List[Session] = []
