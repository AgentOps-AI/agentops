import atexit

from agentops.client.api import ApiClient
from agentops.config import Config
from agentops.exceptions import NoApiKeyException
from agentops.instrumentation import instrument_all
from agentops.logging import logger
from agentops.logging.config import configure_logging, intercept_opentelemetry_logging
from agentops.sdk.core import TracingCore

# Global registry for active session
_active_session = None

# Single atexit handler registered flag
_atexit_registered = False


def _end_active_session():
    """Global handler to end the active session during shutdown"""
    global _active_session
    if _active_session is not None:
        logger.debug("Auto-ending active session during shutdown")
        try:
            from agentops.legacy import end_session

            end_session(_active_session)
        except Exception as e:
            logger.warning(f"Error ending active session during shutdown: {e}")
            # Final fallback: try to end the span directly
            try:
                if hasattr(_active_session, "span") and hasattr(_active_session.span, "end"):
                    _active_session.span.end()
            except:
                pass


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
        # Recreate the Config object to parse environment variables at the time of initialization
        self.config = Config()
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
        if response is None:
            return

        # Save the bearer for use with the v4 API
        self.api.v4.set_auth_token(response["token"])

        # Initialize TracingCore with the current configuration and project_id
        tracing_config = self.config.dict()
        tracing_config["project_id"] = response["project_id"]

        TracingCore.initialize_from_config(tracing_config, jwt=response["token"])

        # Instrument LLM calls if enabled
        if self.config.instrument_llm_calls:
            instrument_all()

        self.initialized = True

        # Register a single global atexit handler for session management
        global _atexit_registered
        if not _atexit_registered:
            atexit.register(_end_active_session)
            _atexit_registered = True

        # Start a session if auto_start_session is True
        session = None
        if self.config.auto_start_session:
            from agentops.legacy import start_session

            # Pass default_tags if they exist
            if self.config.default_tags:
                session = start_session(tags=list(self.config.default_tags))
            else:
                session = start_session()

            # Register this session globally
            global _active_session
            _active_session = session

        return session

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
