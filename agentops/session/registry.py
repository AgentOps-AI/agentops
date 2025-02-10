"""Registry for tracking active sessions"""

import logging
from typing import TYPE_CHECKING, List, Optional, Union
from uuid import UUID

from .signals import session_ended, session_initialized, session_started

if TYPE_CHECKING:
    from .session import Session

_active_sessions = []  # type: List["Session"]
logger = logging.getLogger(__name__)


def add_session(session: "Session") -> None:
    """Add session to active sessions list"""
    if session not in _active_sessions:
        _active_sessions.append(session)
        logger.debug(f"Added session {session.session_id} to registry. Active sessions: {len(_active_sessions)}")
    else:
        logger.debug(f"Session {session.session_id} already in registry")


def remove_session(session: "Session") -> None:
    """Remove session from active sessions list"""
    if session in _active_sessions:
        _active_sessions.remove(session)
        logger.debug(f"Removed session {session.session_id} from registry. Active sessions: {len(_active_sessions)}")
    else:
        logger.debug(f"Session {session.session_id} not found in registry when trying to remove")


def clear_registry() -> None:
    """Clear all sessions from registry - primarily for testing"""
    logger.debug(f"Clearing registry. Removing {len(_active_sessions)} sessions")
    _active_sessions.clear()


def get_active_sessions() -> List["Session"]:
    """Get list of active sessions"""
    return _active_sessions


def get_session_by_id(session_id: Union[str, UUID]) -> "Session":
    """Get session by ID"""
    session_id_str = str(session_id)  # Convert UUID to string if needed
    for session in _active_sessions:
        if str(session.session_id) == session_id_str:
            return session
    raise ValueError(f"Session with ID {session_id} not found")


def get_default_session() -> Optional["Session"]:
    """Get the default session to use when none is specified.

    Returns the only active session if there is exactly one,
    otherwise returns None.
    """
    logger.debug(f"Getting default session. Active sessions: {len(_active_sessions)}")
    if len(_active_sessions) == 1:
        return _active_sessions[0]
    return None


@session_initialized.connect
def on_session_initialized(sender, **kwargs):
    """Add session to registry when initialized"""
    logger.debug(f"Session initialized signal received for {sender.session_id}")
    add_session(sender)


@session_ended.connect
def on_session_ended(sender, **kwargs):
    """Remove session from active sessions list when session ends"""
    logger.debug(f"Session ended signal received for {sender.session_id}")
    remove_session(sender)
