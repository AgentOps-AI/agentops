from typing import List, Optional, Union

from agentops.client.api import ApiClient
from agentops.config import Config
from agentops.exceptions import (AgentOpsClientNotInitializedException,
                                 NoApiKeyException, NoSessionException)
from agentops.instrumentation import instrument_all
from agentops.logging import logger, debug, info, warning, error, log_method_call
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

    @log_method_call(level='info')
    def init(self, **kwargs):
        self.configure(**kwargs)

        if not self.config.api_key:
            error("No API key provided")
            raise NoApiKeyException

        info("Initializing AgentOps client")
        self.api = ApiClient(self.config.endpoint)
        debug(f"API client created with endpoint: {self.config.endpoint}")

        # Prefetch JWT token if enabled
        if self.config.prefetch_jwt_token:
            debug("Prefetching JWT token")
            self.api.v3.fetch_auth_token(self.config.api_key)
            
        # Get the project_id from HttpClient after token fetch
        from agentops.client.http.http_client import HttpClient
        project_id = HttpClient.get_project_id()
        if project_id:
            debug(f"Retrieved project_id: {project_id}")
        
        # Initialize TracingCore with the current configuration and project_id
        tracing_config = self.config.dict()
        if project_id:
            tracing_config['project_id'] = project_id
            debug(f"Adding project_id to tracing configuration")
        
        debug("Initializing TracingCore")
        TracingCore.initialize_from_config(tracing_config)

        # Instrument LLM calls if enabled
        if self.config.instrument_llm_calls:
            debug("Instrumenting LLM calls")
            instrument_all()

        self.initialized = True
        info("AgentOps client initialized successfully")

        if self.config.auto_start_session:
            debug("Auto-starting session")
            return self.start_session()

    @log_method_call(level='debug')
    def configure(self, **kwargs):
        """Update client configuration"""
        debug(f"Configuring client with parameters: {kwargs}")
        self.config.configure(**kwargs)

    @log_method_call(level='info')
    def start_session(self, **kwargs):
        """Start a new session for recording events

        Args:
            tags: Optional list of tags for the session
            inherited_session_id: Optional ID to inherit from another session

        Returns:
            Session or None: New session if successful, None if no API key configured
        """
        debug(f"Starting session with parameters: {kwargs}")

        if not self.initialized:
            # Attempt to initialize the client if not already initialized
            if self.config.auto_init:
                info("Client not initialized, auto-initializing")
                self.init()
            else:
                error("Client not initialized and auto_init is disabled")
                raise AgentOpsClientNotInitializedException

        # This is a placeholder for the actual implementation
        warning('Session start is not yet implemented')
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
