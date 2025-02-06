"""Session management module"""

from .registry import add_session, get_active_sessions, remove_session
from .session import Session, SessionExporter, SessionLogExporter

# For backward compatibility
active_sessions = get_active_sessions()
