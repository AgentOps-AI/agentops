from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Optional, Union, Any
from uuid import UUID

from agentops.config import Configuration
from agentops.enums import EndState
from agentops.helpers import get_ISO_time
from .log_capture import LogCapture

if TYPE_CHECKING:
    from agentops.event import Event, ErrorEvent


@dataclass
class Session:
    """Data container for session state with minimal public API"""

    session_id: UUID
    config: Configuration
    tags: List[str] = field(default_factory=list)
    host_env: Optional[dict] = None
    token_cost: Decimal = field(default_factory=lambda: Decimal(0))
    end_state: str = field(default_factory=lambda: EndState.INDETERMINATE.value)
    end_state_reason: Optional[str] = None
    end_timestamp: Optional[str] = None
    jwt: Optional[str] = None
    video: Optional[str] = None
    event_counts: Dict[str, int] = field(
        default_factory=lambda: {"llms": 0, "tools": 0, "actions": 0, "errors": 0, "apis": 0}
    )
    init_timestamp: str = field(default_factory=get_ISO_time)
    is_running: bool = field(default=True)
    _telemetry: Any = field(init=False, repr=False, default=None)
    _api: Any = field(init=False, repr=False, default=None)
    _manager: Any = field(init=False, repr=False, default=None)
    _otel_exporter: Any = field(init=False, repr=False, default=None)
    _log_capture: LogCapture = field(init=False, repr=False, default=None)

    def __post_init__(self):
        """Initialize session manager"""
        # Convert tags to list first
        if isinstance(self.tags, (str, set)):
            self.tags = list(self.tags)
        elif self.tags is None:
            self.tags = []

        # Initialize API client
        from ..api.session import SessionApiClient

        if not self.config.api_key:
            raise ValueError("API key is required")

        self._api = SessionApiClient(
            endpoint=self.config.endpoint, session_id=self.session_id, api_key=self.config.api_key
        )

        # Then initialize manager
        from .manager import SessionManager

        self._manager = SessionManager(self)
        self.is_running = self._manager.start_session()

        self._log_capture = LogCapture(self)

    # Public API - All delegate to manager
    def add_tags(self, tags: Union[str, List[str]]) -> None:
        """Add tags to session"""
        if self.is_running and self._manager:
            self._manager.add_tags(tags)

    def set_tags(self, tags: Union[str, List[str]]) -> None:
        """Set session tags"""
        if self.is_running and self._manager:
            self._manager.set_tags(tags)

    def record(self, event: Union["Event", "ErrorEvent"], flush_now: bool = False) -> None:
        """Record an event"""
        if self._manager:
            self._manager.record_event(event, flush_now)

    def end_session(
        self,
        end_state: str = EndState.INDETERMINATE.value,
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None,
    ) -> Union[Decimal, None]:
        """End the session"""
        if self._manager:
            return self._manager.end_session(end_state, end_state_reason, video)
        return None

    def create_agent(self, name: str, agent_id: Optional[str] = None) -> Optional[str]:
        """Create a new agent for this session"""
        if self.is_running and self._manager:
            return self._manager.create_agent(name, agent_id)
        return None

    def get_analytics(self) -> Optional[Dict[str, Union[int, str]]]:
        """Get session analytics"""
        if self._manager:
            return self._manager._get_analytics()
        return None

    @property
    def session_url(self) -> str:
        return f"https://app.agentops.ai/drilldown?session_id={self.session_id}"

    @property
    def _tracer_provider(self):
        """For testing compatibility"""
        return self._telemetry._tracer_provider if self._telemetry else None

    def start_log_capture(self):
        """Start capturing terminal output"""
        self._log_capture.start()

    def stop_log_capture(self):
        """Stop capturing terminal output"""
        self._log_capture.stop()