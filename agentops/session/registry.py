"""Registry for tracking active sessions"""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .session import Session

_active_sessions = []  # type: List["Session"]


def add_session(session: "Session") -> None:
    """Add session to active sessions list"""
    if session not in _active_sessions:
        _active_sessions.append(session)


def remove_session(session: "Session") -> None:
    """Remove session from active sessions list"""
    if session in _active_sessions:
        _active_sessions.remove(session)


def get_active_sessions() -> List["Session"]:
    """Get list of active sessions"""
    return _active_sessions
