from __future__ import annotations

from typing import Any, Dict, Optional, Union

from opentelemetry.trace import Span, StatusCode

from agentops.sdk.spanned import SpannedBase
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.span_kinds import SpanKind


class AgentSpan(SpannedBase):
    """
    Represents an agent span, which tracks agent operations.
    
    Agent spans are typically long-running operations that involve multiple steps
    and may include LLM calls, tool usage, and other operations.
    """
    
    def __init__(
        self,
        name: str,
        agent_type: str,
        parent: Optional[Union[SpannedBase, Span]] = None,
        **kwargs
    ):
        """
        Initialize an agent span.
        
        Args:
            name: Name of the agent
            agent_type: Type of agent (e.g., "assistant", "chatbot", "planner")
            parent: Optional parent span or spanned object
            **kwargs: Additional keyword arguments
        """
        # Set default values
        kwargs.setdefault("kind", SpanKind.AGENT)
        kwargs.setdefault("immediate_export", True)  # Agents are typically exported immediately
        
        # Initialize base class
        super().__init__(name=name, parent=parent, **kwargs)
        
        # Store agent-specific attributes
        self._agent_type = agent_type
        
        # Set attributes
        self._attributes.update({
            AgentAttributes.AGENT_NAME: name,
            AgentAttributes.AGENT_ROLE: agent_type,
        })
    
    def record_action(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Record an agent action.
        
        Args:
            action: Name of the action
            details: Optional details about the action
        """
        self.set_attribute("agent.action", action)
        if details:
            for key, value in details.items():
                self.set_attribute(f"agent.action.{key}", value)
        
        # Update the span to trigger immediate export if configured
        self.update()
    
    def record_thought(self, thought: str) -> None:
        """
        Record an agent thought.
        
        Args:
            thought: The thought to record
        """
        self.set_attribute("agent.thought", thought)
        
        # Update the span to trigger immediate export if configured
        self.update()
    
    def record_error(self, error: Union[str, Exception]) -> None:
        """
        Record an agent error.
        
        Args:
            error: The error to record
        """
        error_str = str(error)
        self.set_attribute("agent.error", error_str)
        
        # Update the span to trigger immediate export if configured
        self.update()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result.update({
            "agent_type": self._agent_type,
        })
        return result 