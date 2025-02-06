"""Registry for tracking active sessions"""

import logging
from typing import TYPE_CHECKING, List

from .events import session_ended, session_initialized, session_started

if TYPE_CHECKING:
    from .session import Session

_active_sessions = []  # type: List["Session"]
logger = logging.getLogger(__name__)


def add_session(session: "Session") -> None:
    """Add session to active sessions list"""
    if session not in _active_sessions:
        _active_sessions.append(session)


def remove_session(session: "Session") -> None:
    """Remove session from active sessions list"""
    if session in _active_sessions:
        _active_sessions.remove(session)
        logger.debug(f"Removed session {session.session_id} from registry")
    else:
        logger.debug(f"Session {session.session_id} not found in registry when trying to remove")


def clear_registry() -> None:
    """Clear all sessions from registry - primarily for testing"""
    _active_sessions.clear()


def get_active_sessions() -> List["Session"]:
    """Get list of active sessions"""
    return _active_sessions


def get_session_by_id(session_id: str) -> "Session":
    """Get session by ID"""
    session_id = str(session_id)
    for session in _active_sessions:
        if str(session.session_id) == session_id:
            return session
    raise ValueError(f"Session with ID {session_id} not found")


@session_initialized.connect
def on_session_initialized(sender, **kwargs):
    """Add session to registry when initialized"""
    add_session(sender)


@session_ended.connect
def on_session_ended(sender, **kwargs):
    """Remove session from active sessions list when session ends"""
    logger.debug(f"Session ended signal received for {sender.session_id}")
    remove_session(sender)
