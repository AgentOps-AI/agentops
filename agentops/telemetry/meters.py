"""Metrics module for AgentOps.

This module provides OpenTelemetry-based meters for tracking event counts in AgentOps sessions.
Each meter tracks a specific type of event that was previously counted in the legacy event_counts
dictionary in the Session class.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from opentelemetry import metrics
from opentelemetry.metrics import Counter, Meter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

if TYPE_CHECKING:
    from agentops.session.session import Session

logger = logging.getLogger(__name__)

# Global MeterProvider instance
_meter_provider: Optional[MeterProvider] = None

# Dictionary to store meters for each session
_session_meters = {}


def get_meter_provider() -> MeterProvider:
    """Get or create the global MeterProvider."""
    global _meter_provider
    if _meter_provider is None:
        _meter_provider = MeterProvider(resource=Resource({SERVICE_NAME: "agentops"}))
        metrics.set_meter_provider(_meter_provider)
    return _meter_provider


class SessionMeters:
    """Core session metrics functionality.

    Tracks counts for various events in a session using OpenTelemetry meters.
    """

    def __init__(self, session: Session):
        """Initialize the session meters.
        
        Args:
            session: The session to track metrics for.
        """
        self.session = session
        self.session_id = str(session.session_id)
        
        # Use global provider
        provider = get_meter_provider()
        
        # Create meter
        self.meter = provider.get_meter("agentops.session.meters")
        
        # Create counters for each event type using OpenTelemetry GenAI semantic conventions
        self.llm_counter = self._create_counter("llms", "Number of LLM calls made during the session")
        self.tool_counter = self._create_counter("tools", "Number of tool calls made during the session")
        self.action_counter = self._create_counter("actions", "Number of actions performed during the session")
        self.error_counter = self._create_counter("errors", "Number of errors encountered during the session")
        self.api_counter = self._create_counter("apis", "Number of API calls made during the session")
        
        # Store this meter for the session
        _session_meters[self.session_id] = self
        
        logger.debug(f"[{self.session_id}] Session meters initialized")

    def _create_counter(self, name: str, description: str) -> Counter:
        """Create a counter for tracking a specific event type.
        
        Args:
            name: The name of the event type.
            description: Description of what the counter tracks.
            
        Returns:
            A counter that can be incremented when events occur.
        """
        return self.meter.create_counter(
            f"gen_ai.session.{name}",
            description=description,
            unit="1",
        )

    def increment_llm(self, count: int = 1) -> None:
        """Increment the LLM call counter.
        
        Args:
            count: The amount to increment by.
        """
        self.llm_counter.add(count, {"gen_ai.operation.name": "chat", "session.id": self.session_id})

    def increment_tool(self, count: int = 1) -> None:
        """Increment the tool call counter.
        
        Args:
            count: The amount to increment by.
        """
        self.tool_counter.add(count, {"gen_ai.operation.name": "execute_tool", "session.id": self.session_id})

    def increment_action(self, count: int = 1) -> None:
        """Increment the action counter.
        
        Args:
            count: The amount to increment by.
        """
        self.action_counter.add(count, {"gen_ai.operation.name": "action", "session.id": self.session_id})

    def increment_error(self, count: int = 1) -> None:
        """Increment the error counter.
        
        Args:
            count: The amount to increment by.
        """
        self.error_counter.add(count, {"error.type": "_OTHER", "session.id": self.session_id})

    def increment_api(self, count: int = 1) -> None:
        """Increment the API call counter.
        
        Args:
            count: The amount to increment by.
        """
        self.api_counter.add(count, {"session.id": self.session_id})


def get_session_meters(session_id: str) -> Optional[SessionMeters]:
    """Get meters for a session.
    
    Args:
        session_id: The ID of the session to get meters for.
        
    Returns:
        The session meters if they exist, otherwise None.
    """
    return _session_meters.get(str(session_id)) 