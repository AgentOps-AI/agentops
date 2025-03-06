import uuid
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from agentops.client.api import ApiClient
from agentops.client.api.versions.v3 import V3Client
from agentops.config import Config, ConfigDict
from agentops.exceptions import (AgentOpsClientNotInitializedException,
                                 NoApiKeyException, NoSessionException)
from agentops.instrumentation import instrument_all, uninstrument_all
from agentops.logging import logger
from agentops.session import Session
from agentops.session.registry import get_active_sessions, get_default_session
from agentops.session.state import SessionState


class Client:
    """Singleton client for AgentOps service"""

    config: Config
    _initialized: bool

    api: ApiClient

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(Client, cls).__new__(cls)
        return cls.__instance

    def __init__(self):
        # Only initialize once
        self._initialized = False
        self.config = Config()

    def init(self, **kwargs) -> Union[Session, None]:
        self.configure(**kwargs)

        if not self.config.api_key:
            raise NoApiKeyException

        self.api = ApiClient(self.config.endpoint)

        # Prefetch JWT token if enabled
        if self.config.prefetch_jwt_token:
            self.api.v3.fetch_auth_token(self.config.api_key)

        # Instrument LLM calls if enabled
        if self.config.instrument_llm_calls:
            instrument_all()

        self.initialized = True

        if self.config.auto_start_session:
            return self.start_session()

    def configure(self, **kwargs):
        """Update client configuration"""
        self.config.configure(**kwargs)

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
            session.end(SessionState(end_state))
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
            session.end(SessionState.INDETERMINATE)

    @property
    def initialized(self) -> bool:
        return self._initialized

    @initialized.setter
    def initialized(self, value: bool):
        if self._initialized and self._initialized != value:
            raise ValueError("Client already initialized")
        self._initialized = value

    # ------------------------------------------------------------
    __instance = None
