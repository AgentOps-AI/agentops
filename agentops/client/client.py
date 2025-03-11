from typing import List, Optional, Union

from agentops.client.api import ApiClient
from agentops.client.api.types import AuthTokenResponse
from agentops.config import Config
from agentops.exceptions import (AgentOpsClientNotInitializedException,
                                 NoApiKeyException, NoSessionException)
from agentops.instrumentation import instrument_all
from agentops.logging import logger
from agentops.sdk.core import TracingCore


def get_default_session():
    """Get the default session"""
    raise NotImplementedError


def get_active_sessions():
    """Get all active sessions"""
    raise NotImplementedError


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

    def init(self, **kwargs):
        self.configure(**kwargs)

        if not self.config.api_key:
            raise NoApiKeyException

        self.api = ApiClient(self.config.endpoint)

        # Prefetch JWT token if enabled
        token_data: AuthTokenResponse = self.api.v3.fetch_auth_token(self.config.api_key)

        assert token_data.get(
            'project_id') is not None, f"Could not retrieve project_id from self.api.v3.fetch_auth_token - invalid response {token_data}"

        # Initialize TracingCore with the current configuration and project_id
        tracing_config = self.config.dict()
        tracing_config['project_id'] = token_data['project_id']
        TracingCore.initialize_from_config(tracing_config)

        # Instrument LLM calls if enabled
        if self.config.instrument_llm_calls:
            instrument_all()

        self.initialized = True

        if self.config.auto_start_session:
            return self.start_session()

    def configure(self, **kwargs):
        """Update client configuration"""
        self.config.configure(**kwargs)

    def start_session(self, **kwargs):
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

        raise NotImplementedError('Session start is not yet implemented')

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
