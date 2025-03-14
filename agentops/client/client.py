from typing import List, Optional, Union

from agentops.client.api import ApiClient
from agentops.config import Config
from agentops.exceptions import (AgentOpsClientNotInitializedException,
                                 NoApiKeyException, NoSessionException)
from agentops.instrumentation import instrument_all
from agentops.logging import logger
from agentops.logging.config import (configure_logging,
                                     intercept_opentelemetry_logging)
from agentops.sdk.core import TracingCore


class Client:
    """Singleton client for AgentOps service"""

    config: Config
    _initialized: bool
    __instance = None  # Class variable for singleton pattern

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

        # TODO we may need to initialize logging before importing OTEL to capture all
        configure_logging(self.config)
        intercept_opentelemetry_logging()

        self.api = ApiClient(self.config.endpoint)

        # Prefetch JWT token if enabled
        # TODO: Move this validation somewhere else (and integrate with self.config.prefetch_jwt_token once we have a solution to that)
        response = self.api.v3.fetch_auth_token(self.config.api_key)

        # Initialize TracingCore with the current configuration and project_id
        tracing_config = self.config.dict()
        tracing_config["project_id"] = response["project_id"]

        TracingCore.initialize_from_config(tracing_config, jwt=response["token"])

        # Instrument LLM calls if enabled
        if self.config.instrument_llm_calls:
            instrument_all()

        self.initialized = True

        # Only start a session if auto_start_session is True and we're not already in start_session
        # Prevents infinite recursion
        if self.config.auto_start_session and not getattr(self, "_in_start_session", False):
            from agentops.legacy import start_session

            # Pass the tags from the config to ensure they're included in the session
            start_session(tags=list(self.config.default_tags) if self.config.default_tags else None)

    def configure(self, **kwargs):
        """Update client configuration"""
        self.config.configure(**kwargs)

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
