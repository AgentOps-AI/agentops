"""Registry for tracking active sessions"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast
from uuid import UUID
from weakref import WeakValueDictionary

from opentelemetry import context, trace

from agentops.logging import logger

if TYPE_CHECKING:
    from .session import Session

# Use WeakValueDictionary to allow session garbage collection
_active_sessions: WeakValueDictionary[str, "Session"] = WeakValueDictionary()

# Context key for storing the current session
CURRENT_SESSION_KEY = context.create_key("agentops-current-session")


def add_session(session: "Session") -> None:
    """Add session to active sessions registry and set as current context if none exists."""
    session_id_str = str(session.session_id)
    
    if session_id_str not in _active_sessions:
        _active_sessions[session_id_str] = session
        logger.debug(f"[{session_id_str}] Added to registry. Active sessions: {len(_active_sessions)}")
        
        # Set as current session in context if no session is currently set
        current = get_current_session()
        if current is None:
            set_current_session(session)
    else:
        logger.warning(f"[{session_id_str}] Already in registry. This might imply a programming error. Please report this.")


def remove_session(session: "Session") -> None:
    """Remove session from active sessions registry."""
    session_id_str = str(session.session_id)
    
    if session_id_str in _active_sessions:
        del _active_sessions[session_id_str]
        logger.debug(f"Removed session {session_id_str} from registry. Active sessions: {len(_active_sessions)}")
        
        # If this was the current session in the context, clear it
        current = get_current_session()
        if current is not None and str(current.session_id) == session_id_str:
            clear_current_session()
    else:
        logger.debug(f"Session {session_id_str} not found in registry when trying to remove")


def clear_registry() -> None:
    """Clear all sessions from registry - primarily for testing"""
    logger.debug(f"Clearing registry. Removing {len(_active_sessions)} sessions")
    _active_sessions.clear()
    clear_current_session()


def get_active_sessions() -> List["Session"]:
    """Get list of active sessions"""
    return list(_active_sessions.values())


def get_session_by_id(session_id: Union[str, UUID]) -> "Session":
    """Get session by ID"""
    session_id_str = str(session_id)  # Convert UUID to string if needed
    
    if session_id_str in _active_sessions:
        return _active_sessions[session_id_str]
    
    raise ValueError(f"Session with ID {session_id} not found")


def get_default_session() -> Optional["Session"]:
    """Get the default session to use when none is specified.
    
    First tries to get the current session from context.
    If no current session is set, returns the only active session if there is exactly one,
    otherwise returns None.
    """
    # First try to get from context
    current = get_current_session()
    if current is not None:
        return current
    
    # Fall back to returning the only session if there's exactly one
    logger.debug(f"Getting default session. Active sessions: {len(_active_sessions)}")
    if len(_active_sessions) == 1:
        return next(iter(_active_sessions.values()))
    
    return None


def set_current_session(session: "Session") -> Any:
    """Set the current session in the OpenTelemetry context.
    
    Returns a token that can be used to restore the previous context.
    """
    # Add to registry if not already there
    add_session(session)
    
    # Set in context
    ctx = context.set_value(CURRENT_SESSION_KEY, session)
    token = context.attach(ctx)
    logger.debug(f"[{session.session_id}] Set as current session in context")
    return token


def get_current_session() -> Optional["Session"]:
    """Get the current session from the OpenTelemetry context."""
    value = context.get_value(CURRENT_SESSION_KEY)
    if value is None:
        return None
    return cast("Session", value)


def clear_current_session() -> None:
    """Clear the current session from the OpenTelemetry context."""
    ctx = context.set_value(CURRENT_SESSION_KEY, None)
    context.attach(ctx)
    logger.debug("Cleared current session from context")


# These functions can be used to create context managers for session scope
def use_session(session: "Session") -> Any:
    """Context manager to use a specific session within a scope."""
    return set_current_session(session)


def end_session_scope(token: Any) -> None:
    """End a session scope by detaching the token."""
    context.detach(token)
