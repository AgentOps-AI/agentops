import threading
import uuid
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from .config import Config, ConfigDict
from .exceptions import NoSessionException
from .logging import logger
from .session import Session
from .session.registry import get_active_sessions, get_default_session


class Client:
    """Singleton client for AgentOps service"""
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if not self._initialized:
            self._config = Config()
            self._pre_init_warnings: List[str] = []
            self._initialized = True

    def init(self, **kwargs: ConfigDict) -> Union[Session, None]:
        """
        Initialize the AgentOps client configuration.

        Args:
            api_key (str, optional): API Key for AgentOps services.
            parent_key (str, optional): Organization key for visibility of all user sessions.
            endpoint (str, optional): The endpoint for the AgentOps service.
            max_wait_time (int, optional): Maximum time to wait before flushing queue.
            max_queue_size (int, optional): Maximum size of the event queue.
            default_tags (List[str], optional): Default tags for sessions.
            instrument_llm_calls (bool): Whether to instrument LLM calls.
            auto_start_session (bool): Whether to start a session automatically.
            inherited_session_id (str, optional): Init with existing Session
            skip_auto_end_session (bool): Don't auto-end session based on framework.
        """
        self._config.configure(self, **kwargs)
        
        if self._config.auto_start_session:
            return self.start_session()
        return None

    def configure(self, **kwargs: ConfigDict):
        """Update client configuration"""
        self._config.configure(self, **kwargs)

    def start_session(
        self,
        tags: Optional[List[str]] = None,
        inherited_session_id: Optional[str] = None,
    ) -> Union[Session, None]:
        """Start a new session for recording events
        
        Args:
            tags: Optional list of tags for the session
            inherited_session_id: Optional ID to inherit from another session
            
        Returns:
            Session or None: New session if successful, None if no API key configured
        """
        if not self._config.api_key:
            logger.warning("No API key configured - cannot start session")
            return None

        try:
            session_id = UUID(inherited_session_id) if inherited_session_id else uuid.uuid4()
            session = Session(
                session_id=session_id,
                config=self._config,
                tags=tags or []
            )
            return session
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None

    def end_session(
        self,
        end_state: str,
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None,
        is_auto_end: Optional[bool] = False,
    ):
        """End the current session"""
        session = get_default_session()
        if session:
            session.end(end_state, end_state_reason, video)
        else:
            logger.warning("No active session to end")

    def add_tags(self, tags: List[str]):
        """Add tags to current session"""
        session = get_default_session()
        if session:
            session.add_tags(tags)
        else:
            raise NoSessionException("No active session to add tags to")

    def set_tags(self, tags: List[str]):
        """Set tags for current session"""
        session = get_default_session()
        if session:
            session.set_tags(tags)
        else:
            raise NoSessionException("No active session to set tags for")

    def end_all_sessions(self):
        """End all active sessions"""
        for session in get_active_sessions():
            session.end("Indeterminate", "Forced end via end_all_sessions()")

    def add_pre_init_warning(self, warning: str):
        """Add a warning that occurred before initialization"""
        self._pre_init_warnings.append(warning)

    @property
    def pre_init_warnings(self) -> List[str]:
        """Get warnings that occurred before initialization"""
        return self._pre_init_warnings 
