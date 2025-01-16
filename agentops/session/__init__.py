"""Session management module"""

from .session import Session
from .registry import get_active_sessions, add_session, remove_session

# For backward compatibility
active_sessions = get_active_sessions()

__all__ = ["Session", "active_sessions", "add_session", "remove_session"]
