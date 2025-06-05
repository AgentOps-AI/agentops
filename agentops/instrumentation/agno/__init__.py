"""Agno Agent instrumentation package."""

import logging

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

LIBRARY_NAME = "agno"
LIBRARY_VERSION = __version__

from .instrumentor import AgnoInstrumentor

def get_current_agno_context():
    """
    Get the current Agno agent or workflow context for use by other instrumentations.
    
    This function allows other instrumentations (like LLM providers) to find and use
    the current agent or team context for proper parent-child span relationships.
    
    Returns:
        tuple: (context, span) if found, (None, None) otherwise
    """
    try:
        # Try to get current OpenTelemetry context first
        from opentelemetry import context as otel_context, trace
        current_context = otel_context.get_current()
        current_span = trace.get_current_span(current_context)
        
        # Check if we're already in an agno span (agent, team, or workflow)
        if current_span and hasattr(current_span, 'name'):
            span_name = getattr(current_span, 'name', '')
            if any(keyword in span_name for keyword in ['agno.agent.run', 'agno.team.run', 'agno.workflow']):
                logger.debug(f"Found active agno span: {span_name}")
                return current_context, current_span
        
        return None, None
        
    except Exception as e:
        logger.debug(f"Error getting agno context: {e}")
        return None, None


def get_agno_context_by_session(session_id: str):
    """
    Legacy function for backward compatibility.
    
    Args:
        session_id: Session identifier
        
    Returns:
        tuple: (None, None) - not supported in new implementation
    """
    logger.debug("get_agno_context_by_session is deprecated - context is managed automatically")
    return None, None


# Export attribute handlers for external use
from .attributes.agent import get_agent_run_attributes
from .attributes.team import get_team_run_attributes, get_team_public_run_attributes
from .attributes.tool import get_tool_execution_attributes
from .attributes.metrics import get_metrics_attributes

__all__ = [
    "AgnoInstrumentor",
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "get_current_agno_context",
    "get_agno_context_by_session",
    "get_agent_run_attributes",
    "get_team_run_attributes",
    "get_team_public_run_attributes",
    "get_tool_execution_attributes",
    "get_metrics_attributes"
] 