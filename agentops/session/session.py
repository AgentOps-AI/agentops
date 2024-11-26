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
from agentops.session.exporter import SessionExporter, SessionExporterMixIn


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
    # is_running moved to Session class as a property
    jwt: Optional[str] = None
    tags: Optional[List[str]] = None
    video: Optional[str] = None
    token_cost: Decimal = Decimal(0)

    def __init__(self, **kwargs):
        kwargs.setdefault("event_counts", {event_type.value: 0 for event_type in EventType})
        kwargs.setdefault("init_timestamp", get_ISO_time())
        super().__init__(**kwargs)


class Session(SessionDict, SessionExporterMixIn):
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
        # Initialize SessionDict first with all required attributes
        super().__init__(
            session_id=session_id,
            config=config,
            tags=tags or [],
            host_env=host_env,
            token_cost=Decimal(0),
            end_state=EndState.INDETERMINATE.value,
            end_state_reason=None,
            end_timestamp=None,
            jwt=None,
            video=None,
            event_counts={event_type.value: 0 for event_type in EventType},
            init_timestamp=get_ISO_time(),
        )

        # Initialize threading primitives
        self._lock = threading.Lock()
        self._end_session_lock = threading.Lock()
        self._running = threading.Event()

        # Initialize locks dict
        self._locks = {
            "lifecycle": threading.Lock(),  # Controls session lifecycle operations
            "update_session": threading.Lock(),  # Protects session state updates
            "events": threading.Lock(),  # Protects event queue operations
            "session": threading.Lock(),  # Protects session state updates
            "tags": threading.Lock(),  # Protects tag modifications
            "api": threading.Lock(),  # Protects API calls
        }

        # Initialize SessionExporterMixIn
        SessionExporterMixIn.__init__(self)

        # Set creation timestamp
        self._create_ts = time.monotonic()

        # Initialize API handler
        self.api = SessionApi(self)

        # Start session first to get JWT
        self._start_session()

    def __hash__(self) -> int:
        """Make Session hashable using session_id"""
        return hash(str(self.session_id))

    def __eq__(self, other: object) -> bool:
        """Define equality based on session_id"""
        if not isinstance(other, Session):
            return NotImplemented
        return str(self.session_id) == str(other.session_id)

    @property
    def is_running(self) -> bool:
        """Check if the session is currently running"""
        return self._running.is_set()

    @property
    def config(self) -> Configuration:
        """Get the session's configuration"""
        return self["config"]

    @property
    def session_url(self) -> str:
        """Returns the URL for this session in the AgentOps dashboard."""
        assert self.session_id, "Session ID is required to generate a session URL"
        return f"https://app.agentops.ai/drilldown?session_id={self.session_id}"

    @property
    def session_id(self) -> UUID:
        """Get the session's UUID"""
        return self["session_id"]

    @is_running.setter
    def is_running(self, value: bool) -> None:
        """Set the session's running state"""
        if value:
            self._running.set()
        else:
            self._running.clear()

    def set_video(self, video: str) -> None:
        """Sets a url to the video recording of the session."""
        self.video = video
        self._update_session()

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
                self.exporter.shutdown()

                # Set session end state
                self.end_timestamp = get_ISO_time()
                self.end_state = end_state
                self.end_state_reason = end_state_reason
                if video is not None:
                    self.video = video

                # Mark session as not running before cleanup
                self.is_running = False

                # Get final analytics
                if not (analytics_stats := self.get_analytics()):
                    return None

                # Log analytics
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

        # Ensure event has all required base attributes
        if not hasattr(event, "id"):
            event.id = uuid4()
        if not hasattr(event, "init_timestamp"):
            event.init_timestamp = get_ISO_time()
        if not hasattr(event, "end_timestamp") or event.end_timestamp is None:
            event.end_timestamp = get_ISO_time()

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
            self.api.update_session()

    def get_analytics(self) -> Dict[str, Union[int, str]]:
        """Get session analytics

        Returns:
            Dictionary containing analytics data
        """
        # Implementation that returns a dictionary with the required keys:
        return {
            "LLM calls": 0,  # Replace with actual values
            "Tool calls": 0,
            "Actions": 0,
            "Errors": 0,
            "Duration": "0s",
            "Cost": "0.000000",
        }

    def _format_duration(self, start_time: str, end_time: str) -> str:
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

    def __iter__(self):
        """
        Override the default iterator to yield sessions sorted by init_timestamp.
        If init_timestamp is not available, fall back to _create_ts.
        """
        return iter(
            sorted(
                super().__iter__(),
                key=lambda session: (
                    session.init_timestamp if hasattr(session, "init_timestamp") else session._create_ts
                ),
            )
        )


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
        super().__init__()
        self._lock = threading.RLock()

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
                        session.init_timestamp if hasattr(session, "init_timestamp") else session._create_ts
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
# active_sessions: List[Session] = []
