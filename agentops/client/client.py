import atexit
import asyncio
import threading
from typing import Optional, Any

from agentops.client.api import ApiClient
from agentops.config import Config
from agentops.instrumentation import instrument_all
from agentops.logging import logger
from agentops.logging.config import configure_logging, intercept_opentelemetry_logging
from agentops.sdk.core import TraceContext, tracer
from agentops.legacy import Session

# Global variables to hold the client's auto-started trace and its legacy session wrapper
_client_init_trace_context: Optional[TraceContext] = None
_client_legacy_session_for_init_trace: Optional[Session] = None

# Single atexit handler registered flag
_atexit_registered = False


def _end_init_trace_atexit():
    """Global atexit handler to end the client's auto-initialized trace during shutdown."""
    global _client_init_trace_context, _client_legacy_session_for_init_trace
    if _client_init_trace_context is not None:
        logger.debug("Auto-ending client's init trace during shutdown.")
        try:
            # Use global tracer to end the trace directly
            if tracer.initialized and _client_init_trace_context.span.is_recording():
                tracer.end_trace(_client_init_trace_context, end_state="Shutdown")
        except Exception as e:
            logger.warning(f"Error ending client's init trace during shutdown: {e}")
        finally:
            _client_init_trace_context = None
            _client_legacy_session_for_init_trace = None  # Clear its legacy wrapper too


class Client:
    """Singleton client for AgentOps service"""

    config: Config
    _initialized: bool
    _init_trace_context: Optional[TraceContext] = None  # Stores the context of the auto-started trace
    _legacy_session_for_init_trace: Optional[Session] = (
        None  # Stores the legacy Session wrapper for the auto-started trace
    )

    __instance = None  # Class variable for singleton pattern

    api: ApiClient
    _auth_token: Optional[str] = None
    _project_id: Optional[str] = None
    _auth_lock = threading.Lock()
    _auth_task: Optional[asyncio.Task] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "Client":
        if cls.__instance is None:
            cls.__instance = super(Client, cls).__new__(cls)
            # Initialize instance variables that should only be set once per instance
            cls.__instance._init_trace_context = None
            cls.__instance._legacy_session_for_init_trace = None
            cls.__instance._auth_token = None
            cls.__instance._project_id = None
            cls.__instance._auth_lock = threading.Lock()
            cls.__instance._auth_task = None
        return cls.__instance

    def __init__(self):
        # Initialization of attributes like config, _initialized should happen here if they are instance-specific
        # and not shared via __new__ for a true singleton that can be re-configured.
        # However, the current pattern re-initializes config in init().
        if (
            not hasattr(self, "_initialized") or not self._initialized
        ):  # Ensure init logic runs only once per actual initialization intent
            self.config = Config()  # Initialize config here for the instance
            self._initialized = False
            # self._init_trace_context = None # Already done in __new__
            # self._legacy_session_for_init_trace = None # Already done in __new__

    def get_current_jwt(self) -> Optional[str]:
        """Get the current JWT token."""
        with self._auth_lock:
            return self._auth_token

    def _set_auth_data(self, token: str, project_id: str):
        """Set authentication data thread-safely."""
        with self._auth_lock:
            self._auth_token = token
            self._project_id = project_id

        # Update the HTTP client's project ID
        from agentops.client.http.http_client import HttpClient

        HttpClient.set_project_id(project_id)

    async def _fetch_auth_async(self, api_key: str) -> Optional[dict]:
        """Asynchronously fetch authentication token."""
        try:
            response = await self.api.v3.fetch_auth_token(api_key)
            if response:
                self._set_auth_data(response["token"], response["project_id"])

                # Update V4 client with token
                self.api.v4.set_auth_token(response["token"])

                # Update tracer config with real project ID
                tracing_config = {"project_id": response["project_id"]}
                tracer.update_config(tracing_config)

                logger.debug("Successfully fetched authentication token asynchronously")
                return response
            else:
                logger.debug("Authentication failed - will continue without authentication")
                return None
        except Exception:
            return None

    def _start_auth_task(self, api_key: str):
        """Start the async authentication task."""
        if self._auth_task and not self._auth_task.done():
            return  # Task already running

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Use existing event loop
                self._auth_task = loop.create_task(self._fetch_auth_async(api_key))
            else:
                # Create new event loop in background thread
                def run_async_auth():
                    asyncio.run(self._fetch_auth_async(api_key))

                import threading

                auth_thread = threading.Thread(target=run_async_auth, daemon=True)
                auth_thread.start()
        except RuntimeError:
            # Create new event loop in background thread
            def run_async_auth():
                asyncio.run(self._fetch_auth_async(api_key))

            import threading

            auth_thread = threading.Thread(target=run_async_auth, daemon=True)
            auth_thread.start()

    def init(self, **kwargs: Any) -> None:  # Return type updated to None
        # Recreate the Config object to parse environment variables at the time of initialization
        # This allows re-init with new env vars if needed, though true singletons usually init once.
        self.config = Config()
        self.configure(**kwargs)

        # Only treat as re-initialization if a different non-None API key is explicitly provided
        provided_api_key = kwargs.get("api_key")
        if self.initialized and provided_api_key is not None and provided_api_key != self.config.api_key:
            logger.warning("AgentOps Client being re-initialized with a different API key. This is unusual.")
            # Reset initialization status to allow re-init with new key/config
            self._initialized = False
            if self._init_trace_context and self._init_trace_context.span.is_recording():
                logger.warning("Ending previously auto-started trace due to re-initialization.")
                tracer.end_trace(self._init_trace_context, "Reinitialized")
            self._init_trace_context = None
            self._legacy_session_for_init_trace = None

        if self.initialized:
            logger.debug("AgentOps Client already initialized.")
            # If auto_start_session was true, return the existing legacy session wrapper
            if self.config.auto_start_session:
                return self._legacy_session_for_init_trace
            return None  # If not auto-starting, and already initialized, return None

        if not self.config.api_key:
            logger.warning(
                "No API key provided. AgentOps will initialize but authentication will fail. "
                "Set AGENTOPS_API_KEY environment variable or pass api_key parameter."
            )
            # Continue without API key - spans will be created but exports will fail gracefully

        configure_logging(self.config)
        intercept_opentelemetry_logging()

        self.api = ApiClient(self.config.endpoint)

        # Initialize tracer with JWT provider for dynamic updates
        tracing_config = self.config.dict()
        tracing_config["project_id"] = "temporary"  # Will be updated when auth completes

        # Create JWT provider function for dynamic updates
        def jwt_provider():
            return self.get_current_jwt()

        # Initialize tracer with JWT provider
        tracer.initialize_from_config(tracing_config, jwt_provider=jwt_provider)

        if self.config.instrument_llm_calls:
            instrument_all()

        # Start authentication task only if we have an API key
        if self.config.api_key:
            self._start_auth_task(self.config.api_key)
        else:
            logger.debug("No API key available - skipping authentication task")

        global _atexit_registered
        if not _atexit_registered:
            atexit.register(_end_init_trace_atexit)  # Register new atexit handler
            _atexit_registered = True

        # Auto-start trace if configured
        if self.config.auto_start_session:
            if self._init_trace_context is None or not self._init_trace_context.span.is_recording():
                logger.debug("Auto-starting init trace.")
                trace_name = self.config.trace_name or "default"
                self._init_trace_context = tracer.start_trace(
                    trace_name=trace_name,
                    tags=list(self.config.default_tags) if self.config.default_tags else None,
                    is_init_trace=True,
                )
                if self._init_trace_context:
                    self._legacy_session_for_init_trace = Session(self._init_trace_context)

                    # For backward compatibility, also update the global references in legacy and client modules
                    # These globals are what old code might have been using via agentops.legacy.get_session() or similar indirect access.
                    global _client_init_trace_context, _client_legacy_session_for_init_trace
                    _client_init_trace_context = self._init_trace_context
                    _client_legacy_session_for_init_trace = self._legacy_session_for_init_trace

                    # Update legacy module's _current_session and _current_trace_context
                    # This is tricky; direct access to another module's globals is not ideal.
                    # Prefer explicit calls if possible, but for maximum BC:
                    try:
                        import agentops.legacy

                        agentops.legacy._current_session = self._legacy_session_for_init_trace
                        agentops.legacy._current_trace_context = self._init_trace_context
                    except ImportError:
                        pass  # Should not happen

                else:
                    logger.error("Failed to start the auto-init trace.")
                    # Even if auto-start fails, core services up to the tracer might be initialized.
                    # Set self.initialized to True if tracer is up, but return None.
                    self._initialized = tracer.initialized
                    return None  # Failed to start trace

            self._initialized = True  # Successfully initialized and auto-trace started (if configured)
            # For backward compatibility, return the legacy session wrapper when auto_start_session=True
            return self._legacy_session_for_init_trace
        else:
            logger.debug("Auto-start session is disabled. No init trace started by client.")
            self._initialized = True  # Successfully initialized, just no auto-trace
            return None  # No auto-session, so return None

    def configure(self, **kwargs: Any) -> None:
        """Update client configuration"""
        self.config.configure(**kwargs)

    @property
    def initialized(self) -> bool:
        return self._initialized

    @initialized.setter
    def initialized(self, value: bool) -> None:
        if self._initialized and self._initialized != value:
            # Allow re-setting to False if we are intentionally re-initializing
            # This logic is now partly in init() to handle re-init cases
            pass
        self._initialized = value

    # ------------------------------------------------------------
    # Remove the old __instance = None at the end of the class definition if it's a repeat
    # __instance = None # This was a class variable, should be defined once

    # Make _init_trace_context and _legacy_session_for_init_trace accessible
    # to the atexit handler if it becomes a static/class method or needs access
    # For now, the atexit handler is global and uses global vars copied from these.

    # Deprecate and remove the old global _active_session from this module.
    # Consumers should use agentops.start_trace() or rely on the auto-init trace.
    # For a transition, the auto-init trace's legacy wrapper is set to legacy module's globals.
