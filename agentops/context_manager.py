"""
Context manager for AgentOps SDK initialization and lifecycle management.
"""

from typing import Optional, Any, Dict
from opentelemetry import context as context_api

from agentops.logging import logger
from agentops.sdk.core import TracingCore, TraceContext
from agentops.legacy import Session


class AgentOpsContextManager:
    """
    Context manager for AgentOps SDK that handles initialization and automatic cleanup.

    This class enables the following usage pattern:

        with agentops.init(api_key="...") as session:
            # Your agent code here
            pass
        # Trace automatically ends here

    It ensures that traces are properly ended even if exceptions occur.
    """

    def __init__(self, client, init_kwargs: Dict[str, Any]):
        """
        Initialize the context manager.

        Args:
            client: The AgentOps Client instance
            init_kwargs: Keyword arguments to pass to client.init()
        """
        self.client = client
        self.init_kwargs = init_kwargs
        self.init_result = None
        self.trace_context: Optional[TraceContext] = None
        self.managed_session: Optional[Session] = None
        self._created_trace = False
        self._context_token: Optional[context_api.Token] = None

    def __enter__(self) -> Optional[Session]:
        """
        Enter the context manager.

        This method:
        1. Initializes the client if not already initialized
        2. Starts a trace if auto_start_session is False
        3. Returns a Session object for the active trace

        Returns:
            Session object for the active trace, or None if initialization fails
        """
        # Perform initialization
        self.init_result = self.client.init(**self.init_kwargs)

        # If init returned a Session (auto_start_session=True), use it
        # Check for Session by checking if it has the expected attributes
        if self.init_result is not None and hasattr(self.init_result, "trace_context"):
            self.managed_session = self.init_result
            return self.managed_session

        # Otherwise, check if we should start a trace for this context
        tracing_core = TracingCore.get_instance()
        if not tracing_core.initialized:
            logger.warning("TracingCore not initialized after client.init(). Cannot start context trace.")
            return None

        # If auto_start_session was False or None, start a trace for this context
        auto_start = self.init_kwargs.get("auto_start_session")
        if auto_start is False or auto_start is None:
            trace_name = self.init_kwargs.get("trace_name", "context_session")
            tags = self.init_kwargs.get("default_tags")

            self.trace_context = tracing_core.start_trace(trace_name=trace_name, tags=tags)
            if self.trace_context:
                self._created_trace = True
                self.managed_session = Session(self.trace_context)
                logger.debug(f"Started context-managed trace: {trace_name}")
            else:
                logger.error("Failed to start trace for context manager")

        return self.managed_session

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> bool:
        """
        Exit the context manager.

        This method:
        1. Determines the appropriate end state based on exceptions
        2. Ends any trace that was created by this context
        3. Does NOT end traces that were auto-started by init()

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        Returns:
            False to propagate any exceptions
        """
        tracing_core = TracingCore.get_instance()
        if not tracing_core.initialized:
            return False

        # Determine end state based on exception
        if exc_type is not None:
            end_state = "Error"
            if exc_val:
                logger.debug(f"Context manager exiting with exception: {exc_val}")
        else:
            end_state = "Success"

        # Only end traces that we created in __enter__
        if self._created_trace and self.trace_context:
            try:
                tracing_core.end_trace(self.trace_context, end_state)
                logger.debug(f"Ended context-managed trace with state: {end_state}")
            except Exception as e:
                logger.error(f"Error ending context-managed trace: {e}")

        # For auto-started sessions, we don't end them here
        # They will be ended by the existing atexit handler or manually
        elif self.managed_session and hasattr(self.managed_session, "trace_context"):
            logger.debug("Not ending auto-started session in context manager exit")

        # Don't suppress exceptions
        return False

    def __getattr__(self, name: str) -> Any:
        """
        Delegate attribute access to the managed session.

        This allows the context manager to be used as if it were the session itself.
        """
        if self.managed_session:
            return getattr(self.managed_session, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


class InitializationProxy:
    """
    A proxy object that can act as both a regular return value and a context manager.

    This allows agentops.init() to be used in both ways:
    - session = agentops.init(...)  # Regular usage
    - with agentops.init(...) as session:  # Context manager usage
    """

    def __init__(self, client, init_kwargs: Dict[str, Any]):
        """
        Initialize the proxy.

        Args:
            client: The AgentOps Client instance
            init_kwargs: Keyword arguments for initialization
        """
        self.client = client
        self.init_kwargs = init_kwargs
        self._result = None
        self._initialized = False

        # Immediately initialize the client to maintain backward compatibility
        # This ensures that agentops._client.initialized is True after init()
        self._ensure_initialized()

    def _ensure_initialized(self):
        """Ensure the client is initialized for non-context usage."""
        if not self._initialized:
            try:
                self._result = self.client.init(**self.init_kwargs)
                self._initialized = True
            except Exception as e:
                self._initialized = True  # Mark as attempted
                self._result = None
                # Re-raise the exception so it propagates to the caller
                raise e

    def __enter__(self):
        """
        Delegate to AgentOpsContextManager for context manager usage.
        """
        ctx_manager = AgentOpsContextManager(self.client, self.init_kwargs)
        self._ctx_manager = ctx_manager
        return ctx_manager.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Delegate to AgentOpsContextManager for context manager usage.

        This ensures proper cleanup following OpenTelemetry patterns.
        """
        if hasattr(self, "_ctx_manager"):
            return self._ctx_manager.__exit__(exc_type, exc_val, exc_tb)
        return False

    def __getattr__(self, name: str) -> Any:
        """
        For non-context usage, initialize and delegate to the result.

        This allows code like:
        session = agentops.init(...)
        session.record(event)  # This triggers initialization
        """
        # Special handling for certain attributes to avoid infinite recursion
        if name.startswith("_"):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

        self._ensure_initialized()
        if self._result is not None:
            return getattr(self._result, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __bool__(self) -> bool:
        """
        Support boolean evaluation.

        This allows code like:
        if agentops.init(...):
            # Initialization successful
        """
        try:
            self._ensure_initialized()
            return bool(self._result)
        except Exception:
            return False

    def __repr__(self) -> str:
        """String representation that clearly identifies this as a proxy."""
        if self._initialized:
            return f"<InitializationProxy(result={repr(self._result)})>"
        return "<InitializationProxy(pending)>"

    def __eq__(self, other) -> bool:
        """Support equality comparison."""
        self._ensure_initialized()
        return self._result == other

    def __ne__(self, other) -> bool:
        """Support inequality comparison."""
        return not self.__eq__(other)

    def __hash__(self) -> int:
        """Support hashing."""
        self._ensure_initialized()
        return hash(self._result) if self._result else hash(None)

    def __str__(self) -> str:
        """String conversion."""
        try:
            self._ensure_initialized()
            if self._result is not None and hasattr(self._result, "__str__"):
                return str(self._result)
            return "None"
        except Exception:
            return "<InitializationProxy(failed)>"

    def get_wrapped_result(self):
        """
        Get the actual wrapped result object.

        This method provides explicit access to the wrapped object
        for cases where direct access is needed.

        Returns:
            The actual result object from client.init()
        """
        self._ensure_initialized()
        return self._result

    def get_proxy_type(self) -> str:
        """
        Get the type of this proxy for debugging purposes.

        This method makes it clear that this is a proxy object,
        which helps with debugging and introspection.

        Returns:
            String identifying this as an InitializationProxy
        """
        return "InitializationProxy"

    def is_context_manager(self) -> bool:
        """
        Check if this proxy can be used as a context manager.

        Returns:
            True, since this proxy supports context manager protocol
        """
        return True

    def __len__(self) -> int:
        """Support len() function."""
        self._ensure_initialized()
        if self._result is not None and hasattr(self._result, "__len__"):
            return len(self._result)
        raise TypeError(f"object of type '{self.__class__.__name__}' has no len()")

    def __iter__(self):
        """Support iteration."""
        self._ensure_initialized()
        if self._result is not None and hasattr(self._result, "__iter__"):
            return iter(self._result)
        raise TypeError(f"'{self.__class__.__name__}' object is not iterable")

    def __contains__(self, item) -> bool:
        """Support 'in' operator."""
        self._ensure_initialized()
        if self._result is not None and hasattr(self._result, "__contains__"):
            return item in self._result
        return False

    def __getitem__(self, key):
        """Support indexing and slicing."""
        self._ensure_initialized()
        if self._result is not None and hasattr(self._result, "__getitem__"):
            return self._result[key]
        raise TypeError(f"'{self.__class__.__name__}' object is not subscriptable")

    def __setitem__(self, key, value):
        """Support item assignment."""
        self._ensure_initialized()
        if self._result is not None and hasattr(self._result, "__setitem__"):
            self._result[key] = value
        else:
            raise TypeError(f"'{self.__class__.__name__}' object does not support item assignment")

    def __delitem__(self, key):
        """Support item deletion."""
        self._ensure_initialized()
        if self._result is not None and hasattr(self._result, "__delitem__"):
            del self._result[key]
        else:
            raise TypeError(f"'{self.__class__.__name__}' object doesn't support item deletion")

    def __call__(self, *args, **kwargs):
        """Support calling the proxy as a function."""
        self._ensure_initialized()
        if self._result is not None and callable(self._result):
            return self._result(*args, **kwargs)
        raise TypeError(f"'{self.__class__.__name__}' object is not callable")
