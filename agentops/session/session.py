from __future__ import annotations

import asyncio
import functools
import json
import sys  # Add this at the top with other imports
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Deque, Dict, List, Optional, Sequence, Union
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
from agentops.event import ActionEvent, ErrorEvent, Event, LLMEvent, ToolEvent
from agentops.exceptions import ApiServerException
from agentops.helpers import filter_unjsonable, get_ISO_time, safe_serialize
from agentops.http_client import HttpClient, Response
from agentops.log_config import logger
from agentops.session.api import SessionApi
from agentops.session.exporter import SessionExporter, SessionExporterMixIn

try:
    from typing import DefaultDict  # Python 3.9+
except ImportError:
    from typing_extensions import DefaultDict  # Python 3.8 and below


@dataclass
class SessionState:
    """Encapsulates all session state data"""

    session_id: UUID
    config: Configuration
    tags: List[str] = field(default_factory=list)
    host_env: Optional[dict] = None
    token_cost: Decimal = Decimal(0)
    end_state: str = field(default_factory=lambda: EndState.INDETERMINATE.value)
    end_state_reason: Optional[str] = None
    end_timestamp: Optional[str] = None
    jwt: Optional[str] = None
    video: Optional[str] = None
    event_counts: Dict[str, int] = field(default_factory=lambda: {"llms": 0, "tools": 0, "actions": 0, "errors": 0})
    init_timestamp: str = field(default_factory=get_ISO_time)
    recent_events: Deque[Union[Event, ErrorEvent]] = field(default_factory=lambda: deque(maxlen=20))


class Session(SessionExporterMixIn):
    """
    Represents a session of events, with a start and end state.
    """

    def __init__(
        self,
        session_id: UUID,
        config: Configuration,
        tags: Optional[List[str]] = None,
        host_env: Optional[dict] = None,
    ):
        # Initialize session state
        self.state = SessionState(session_id=session_id, config=config, tags=tags or [], host_env=host_env)

        # Initialize threading primitives
        self._locks = {
            "lifecycle": threading.Lock(),  # Controls session lifecycle operations
            "update_session": threading.Lock(),  # Protects session state updates
            "events": threading.Lock(),  # Protects event queue operations
            "session": threading.Lock(),  # Protects session state updates
            "tags": threading.Lock(),  # Protects tag modifications
            "api": threading.Lock(),  # Protects API calls
        }
        self._running = threading.Event()

        # Initialize components
        self.api = SessionApi(self)
        SessionExporterMixIn.__init__(self)

        # Start session
        self._start_session()

    def __hash__(self) -> int:
        """Make Session hashable using session_id"""
        return hash(str(self.state.session_id))

    def __eq__(self, other: object) -> bool:
        """Define equality based on session_id"""
        if not isinstance(other, Session):
            return NotImplemented
        return str(self.state.session_id) == str(other.state.session_id)

    ## >>>> Allow transparent access to state attributes >>>>
    def __getattr__(self, name: str) -> Any:
        """Transparently get attributes from state if they don't exist on session"""
        # Avoid recursion by checking if state exists first
        if name == "state":
            raise AttributeError(f"'{type(self).__name__}' object has no attribute 'state'")

        # Only check state attributes if state exists
        if hasattr(self, "state"):
            if hasattr(self.state, name):
                return getattr(self.state, name)

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        """Transparently set attributes on state if they exist there"""
        # Handle initialization of core attributes directly
        if name in ("state", "_session_attrs", "_locks", "_running", "api"):
            super().__setattr__(name, value)
            return

        # Initialize _session_attrs if needed
        if not hasattr(self, "_session_attrs"):
            super().__setattr__("_session_attrs", set())

        if name in self._session_attrs:
            # This is a session attribute, set it directly
            super().__setattr__(name, value)
        elif hasattr(self, "state") and hasattr(self.state, name):
            # This is a state attribute, set it on state
            setattr(self.state, name, value)
        else:
            # New attribute, add it to session
            self._session_attrs.add(name)
            super().__setattr__(name, value)

    ## <<<< End of transparent access to state attributes <<<<
    @property
    def is_running(self) -> bool:
        """Check if the session is currently running"""
        return self._running.is_set()

    @property
    def config(self) -> Configuration:
        """Get the session's configuration"""
        return self.state.config

    @property
    def session_url(self) -> str:
        """Returns the URL for this session in the AgentOps dashboard."""
        assert self.state.session_id, "Session ID is required to generate a session URL"
        return f"https://app.agentops.ai/drilldown?session_id={self.state.session_id}"

    @property
    def session_id(self) -> UUID:
        """Get the session's UUID"""
        return self.state.session_id

    @is_running.setter
    def is_running(self, value: bool) -> None:
        """Set the session's running state"""
        if value:
            self._running.set()
        else:
            self._running.clear()

    def set_video(self, video: str) -> None:
        """Sets a url to the video recording of the session."""
        self.state.video = video
        self._update_session()

    def end_session(
        self,
        end_state: str = "Indeterminate",
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None,
    ) -> Union[Decimal, None]:
        """End the current session and clean up resources"""
        with self._locks["lifecycle"]:
            if not self.is_running:
                return None

            try:
                self._exporter.shutdown()
                self._exporter.flush()

                # Update session state
                self.state.end_state = end_state
                self.state.end_timestamp = get_ISO_time()
                self.state.end_state_reason = end_state_reason
                if video is not None:
                    self.state.video = video

                self.is_running = False
                self.api.update_session()

                # Get analytics and log stats
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
                active_sessions.remove(self)
                logger.info(
                    colored(
                        f"\x1b[34mSession Replay: {self.session_url}\x1b[0m",
                        "blue",
                    )
                )
            return self.token_cost

    def add_tags(self, tags: List[str]) -> None:
        """Append to session tags at runtime."""
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

    def set_tags(self, tags: List[str]) -> None:
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

    def record(self, event: Union[Event, ErrorEvent], flush_now=False) -> None:
        """Record an event using OpenTelemetry spans"""
        if not self.is_running:
            return

        with self._locks["events"]:  # Add lock to prevent race conditions
            # FIXME: This is hacky! Better handle ErrorEvent differently
            if not hasattr(event, "id"):
                event.id = uuid4()

            # Handle ErrorEvent separately since it doesn't inherit from Event
            if isinstance(event, ErrorEvent):
                if not hasattr(event, "timestamp"):
                    event.timestamp = get_ISO_time()
                # Update error count
                self.state.event_counts["errors"] += 1
            else:
                if not hasattr(event, "init_timestamp"):
                    event.init_timestamp = get_ISO_time()
                if not hasattr(event, "end_timestamp") or event.end_timestamp is None:
                    event.end_timestamp = get_ISO_time()
                # Update appropriate event count based on event type
                if isinstance(event, LLMEvent):
                    self.state.event_counts["llms"] += 1
                elif isinstance(event, ToolEvent):
                    self.state.event_counts["tools"] += 1
                elif isinstance(event, ActionEvent):
                    self.state.event_counts["actions"] += 1

            # Add event to recent events - deque will automatically maintain max size
            self.state.recent_events.append(event)

            # Delegate to OTEL-specific recording logic
            self._record_otel_event(event, flush_now)

    def _start_session(self) -> bool:
        """Initialize the session via API"""
        with self._locks["lifecycle"]:
            if not self.api.create_session():
                return False
            self.is_running = True
            return True

    def _update_session(self) -> None:
        """Update session state via API"""
        with self._locks["update_session"]:
            if not self.is_running:
                return
            response_body, _ = self.api.update_session()
            if response_body and "token_cost" in response_body:
                self.state.token_cost = Decimal(str(response_body["token_cost"]))

    def get_analytics(self) -> Dict[str, Union[int, str]]:
        """Get session analytics

        Returns:
            Dictionary containing analytics data including:
            - LLM calls count
            - Tool calls count
            - Actions count
            - Errors count
            - Duration
            - Cost
        """

        formatted_duration = self._format_duration(self.state.init_timestamp, self.state.end_timestamp)

        return {
            "LLM calls": self.state.event_counts.get("llms", 0),
            "Tool calls": self.state.event_counts.get("tools", 0),
            "Actions": self.state.event_counts.get("actions", 0),
            "Errors": self.state.event_counts.get("errors", 0),
            "Duration": formatted_duration,
            "Cost": self._format_token_cost(self.state.token_cost),
        }

    def _format_duration(self, start_time: str, end_time: Optional[str] = None) -> str:
        """Format duration between two timestamps"""
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))

        # If no end time provided, use current time
        if end_time is None:
            end = datetime.now(timezone.utc)
        else:
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

    def _get_token_cost(self, response_body: dict) -> Decimal:
        """Extract token cost from response"""
        token_cost = response_body.get("token_cost", "unknown")
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

    # >>> Forward state attributes for serialization
    def __iter__(self):
        """Make Session iterable for dict() conversion"""
        for key, value in self.state.__dict__.items():
            yield key, value

    def __getstate__(self) -> dict:
        """Return the state for serialization"""
        return self.state.__dict__

    # >>> End of forward state attributes for serialization

    @property
    def recent_events(self) -> List[Union[Event, ErrorEvent]]:
        """Get the most recent events (up to 20) recorded in this session"""
        return list(self.state.recent_events)

    def flush(self) -> None:
        """Flush the session exporter and span processor"""
        # with self._locks["events"]:
        if not self.is_running:
            return
        try:
            # Forces the BatchSpanProcessor to immediately process any spans in its current batch buffer.
            # The BatchSpanProcessor normally batches spans for efficiency and processes them based on configured batch size or schedule.
            self._span_processor.force_flush()
            # This flushes the exporter itself, which is responsible for actually sending the data to the backend system.
            # The exporter may have its own internal buffering or retry mechanisms.
            self._exporter.flush()
        except Exception as e:
            logger.error(f"Error during flush: {e}")


class SessionsCollection(WeakSet):
    """
    A custom collection for managing Session objects that combines WeakSet's automatic cleanup
    with list-like indexing capabilities.

    This class is needed because:
    1. We want WeakSet's automatic cleanup of unreferenced sessions
    2. We need to access sessions by index (e.g., self._sessions[0]) for backwards compatibility
    3. Standard WeakSet doesn't support indexing
    """

    def __init__(self):
        self._lock = threading.RLock()
        super().__init__()

    def __getitem__(self, index: int) -> Session:
        """
        Enable indexing into the collection (e.g., sessions[0]).
        """
        with self._lock:
            # Convert to list for indexing since sets aren't ordered
            items = list(self)
            return items[index]

    def __setitem__(self, index: int, session: Session) -> None:
        """
        Enable item assignment (e.g., sessions[0] = new_session).
        """
        with self._lock:
            items = list(self)
            if 0 <= index < len(items):
                self.remove(items[index])
                self.add(session)
            else:
                raise IndexError("list assignment index out of range")

    def __iter__(self):
        """
        Override the default iterator to yield sessions sorted by init_timestamp.
        If init_timestamp is not available, fall back to _create_ts.

        WARNING: Using _create_ts as a fallback for ordering may lead to unexpected results
        if init_timestamp is not set correctly.
        """
        with self._lock:
            return iter(
                sorted(
                    super().__iter__(),
                    key=lambda session: (
                        session.state.init_timestamp
                        if hasattr(session, "state") and hasattr(session.state, "init_timestamp")
                        else session._create_ts
                    ),
                )
            )

    def append(self, session: Session) -> None:
        """Append a session to the collection"""
        with self._lock:
            super().add(session)

    def remove(self, session: Session) -> None:
        """Remove a session from the collection"""
        with self._lock:
            super().discard(session)

    def __len__(self) -> int:
        """Return the number of sessions in the collection"""
        with self._lock:
            return len(list(super().__iter__()))

    def index(self, session: Session) -> int:
        """Return the index of a session in the collection"""
        with self._lock:
            return list(super().__iter__()).index(session)


active_sessions = SessionsCollection()
