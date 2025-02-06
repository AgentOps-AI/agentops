"""Registry for tracking active sessions"""

from typing import TYPE_CHECKING, List

from .events import session_ended, session_started

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


def get_session_by_id(session_id: str) -> "Session":
    session_id = str(session_id)
    """Get session by ID"""
    for session in _active_sessions:
        if session.session_id == session_id:
            return session
    raise ValueError(f"Session with ID {session_id} not found")


@session_started.connect
def on_session_started(sender):
    breakpoint()
    """Initialize session tracer when session starts"""
    _active_sessions.append(sender)


@session_ended.connect
def on_session_ended(sender):
    """Remove session from active sessions list when session ends"""
    breakpoint()
    _active_sessions.remove(sender)
