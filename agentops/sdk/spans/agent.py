from __future__ import annotations

from typing import Any, Dict, Optional, Union

from opentelemetry.trace import Span, StatusCode

from agentops.sdk.traced import TracedObject
from agentops.logging import logger
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.span_kinds import SpanKind
from agentops.semconv.core import CoreAttributes


class AgentSpan(TracedObject):
    """
    Represents an agent span, which tracks agent operations.
    
    Agent spans are typically long-running operations that involve multiple steps
    and may include LLM calls, tool usage, and other operations.
    """
    
    def __init__(
        self,
        name: str,
        agent_type: str,
        parent: Optional[Union[TracedObject, Span]] = None,
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
        
        logger.debug(f"AgentSpan initialized: name={name}, agent_type={agent_type}")
    
    def record_action(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Record an agent action.
        
        Args:
            action: Name of the action
            details: Optional details about the action
        """
        self.set_attribute(SpanKind.AGENT_ACTION, action)
        if details:
            for key, value in details.items():
                self.set_attribute(f"{SpanKind.AGENT_ACTION}.{key}", value)
        
        detail_str = f", details={list(details.keys()) if details else 'None'}"
        logger.debug(f"AgentSpan action recorded: {self.name}, action={action}{detail_str}")
        
        # Update the span to trigger immediate export if configured
        self.update()
    
    def record_thought(self, thought: str) -> None:
        """
        Record an agent thought.
        
        Args:
            thought: The thought to record
        """
        self.set_attribute(SpanKind.AGENT_THINKING, thought)
        
        # Log a truncated version of the thought to avoid huge log lines
        log_thought = thought[:100] + "..." if len(thought) > 100 else thought
        logger.debug(f"AgentSpan thought recorded: {self.name}, thought={log_thought}")
        
        # Update the span to trigger immediate export if configured
        self.update()
    
    def record_error(self, error: Union[str, Exception]) -> None:
        """
        Record an agent error.
        
        Args:
            error: The error to record
        """
        error_str = str(error)
        self.set_attribute(CoreAttributes.ERROR_MESSAGE, error_str)
        
        # Log a truncated version of the error to avoid huge log lines
        log_error = error_str[:100] + "..." if len(error_str) > 100 else error_str
        logger.debug(f"AgentSpan error recorded: {self.name}, error={log_error}")
        
        # Update the span to trigger immediate export if configured
        self.update()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result.update({
            "agent_type": self._agent_type,
        })
        logger.debug(f"AgentSpan converted to dict: {self.name}, agent_type={self._agent_type}")
        return result 