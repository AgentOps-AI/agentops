from contextvars import ContextVar
from typing import Optional
from agentops.session import Session, get_default_session

# Context variable to track current session
current_session: ContextVar[Optional[Session]] = ContextVar('current_session', default=None)

def get_current_session() -> Optional[Session]:
    """Get the current session from context or default"""
    session = current_session.get()
    if session is None:
        session = get_default_session()
    return session

def set_current_session(session: Optional[Session]) -> None:
    """Set the current session in context"""
    current_session.set(session) 