"""Context utilities for AgentOps instrumentation.

This module provides utilities for working with OpenTelemetry context
and retrieving the current session.
"""

from typing import Optional, Union
from uuid import UUID

from opentelemetry import context

from agentops.session.registry import get_default_session

# Key for storing session ID in OpenTelemetry context
SESSION_ID_KEY = "agentops.session.id"


def get_current_session():
    """Get the current session from OpenTelemetry context.
    
    This function first checks if there's a session ID in the current
    OpenTelemetry context. If found, it retrieves the session by ID.
    If not found, it falls back to the default session.
    
    Returns:
        The current session if available, otherwise None.
    """
    # Try to get session ID from current context
    ctx = context.get_current()
    session_id = ctx.get(SESSION_ID_KEY)
    
    if session_id:
        # Import here to avoid circular imports
        from agentops.session.registry import get_session_by_id
        try:
            # Ensure session_id is properly typed
            return get_session_by_id(str(session_id))
        except ValueError:
            # Session ID in context but session not found
            pass
    
    # Fall back to default session
    return get_default_session()


def set_session_in_context(session_id: Union[str, UUID]):
    """Set the session ID in the current OpenTelemetry context.
    
    Args:
        session_id: The ID of the session to set in context.
        
    Returns:
        The updated context.
    """
    return context.set_value(SESSION_ID_KEY, str(session_id)) 
