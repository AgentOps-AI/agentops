import uuid
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from agentops._singleton import conditional_singleton

from .config import Config, ConfigDict
from .exceptions import (AgentOpsClientNotInitializedException,
                         NoApiKeyException, NoSessionException)
from .instrumentation import instrument_all, uninstrument_all
from .logging import logger
from .session import Session
from .session.registry import get_active_sessions, get_default_session


@conditional_singleton
class Client:
    """Singleton client for AgentOps service"""

    config: Config
    _initialized = False

    def __init__(self):
        self._initialized = False
        self.config = Config()
        self._pre_init_warnings: List[str] = []


    def init(self, **kwargs) -> Union[Session, None]:
        self.configure(**kwargs)

        # Instrument LLM calls if enabled
        if self.config.instrument_llm_calls:
            instrument_all()

        self.initialized = True

        if self.config.auto_start_session:
            return self.start_session()

    def configure(self, **kwargs):
        """Update client configuration"""
        self.config.configure(self, **kwargs)

    def start_session(self, **kwargs) -> Union[Session, None]:
        """Start a new session for recording events

        Args:
            tags: Optional list of tags for the session
            inherited_session_id: Optional ID to inherit from another session

        Returns:
            Session or None: New session if successful, None if no API key configured
        """

        if not self.initialized:
            # Attempt to initialize the client if not already initialized
            if self.config.auto_init:
                self.init()
            else:
                raise AgentOpsClientNotInitializedException

        if not self.config.api_key:
            raise NoApiKeyException

        try:
            return Session(config=self.config, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            if not self.config.fail_safe:
                raise
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

    @property
    def initialized(self) -> bool:
        return self._initialized

    @initialized.setter
    def initialized(self, value: bool):
        if self._initialized and self._initialized != value:
            raise ValueError("Client already initialized")
        self._initialized = value
