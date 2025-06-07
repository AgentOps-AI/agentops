"""
OpenTelemetry Instrumentation for concurrent.futures module.

This instrumentation automatically patches ThreadPoolExecutor to ensure proper
context propagation across thread boundaries, preventing "NEW TRACE DETECTED" issues.
"""

import contextvars
import functools
from typing import Any, Callable, Collection, Optional, Tuple, TypeVar

from concurrent.futures import ThreadPoolExecutor, Future

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor

from agentops.logging import logger

# Store original methods to restore during uninstrumentation
_original_init = None
_original_submit = None

# Type variables for better typing
T = TypeVar("T")
R = TypeVar("R")


def _context_propagating_init(original_init: Callable) -> Callable:
    """Wrap ThreadPoolExecutor.__init__ to set up context-aware initializer."""

    @functools.wraps(original_init)
    def wrapped_init(
        self: ThreadPoolExecutor,
        max_workers: Optional[int] = None,
        thread_name_prefix: str = "",
        initializer: Optional[Callable] = None,
        initargs: Tuple = (),
    ) -> None:
        # Capture the current context when the executor is created
        main_context = contextvars.copy_context()

        def context_aware_initializer() -> None:
            """Initializer that sets up the captured context in each worker thread."""
            logger.debug("[ConcurrentFuturesInstrumentor] Setting up context in worker thread")

            # Set the main context variables in this thread
            for var, value in main_context.items():
                try:
                    var.set(value)
                except Exception as e:
                    logger.debug(f"[ConcurrentFuturesInstrumentor] Could not set context var {var}: {e}")

            # Run user's initializer if provided
            if initializer and callable(initializer):
                try:
                    if initargs:
                        initializer(*initargs)
                    else:
                        initializer()
                except Exception as e:
                    logger.error(f"[ConcurrentFuturesInstrumentor] Error in user initializer: {e}")
                    raise

            logger.debug("[ConcurrentFuturesInstrumentor] Worker thread context setup complete")

        # Create executor with context-aware initializer
        prefix = f"AgentOps-{thread_name_prefix}" if thread_name_prefix else "AgentOps-Thread"

        # Call original init with our context-aware initializer
        original_init(
            self,
            max_workers=max_workers,
            thread_name_prefix=prefix,
            initializer=context_aware_initializer,
            initargs=(),  # We handle initargs in our wrapper
        )

        logger.debug("[ConcurrentFuturesInstrumentor] ThreadPoolExecutor initialized with context propagation")

    return wrapped_init


def _context_propagating_submit(original_submit: Callable) -> Callable:
    """Wrap ThreadPoolExecutor.submit to ensure context propagation."""

    @functools.wraps(original_submit)
    def wrapped_submit(self: ThreadPoolExecutor, func: Callable[..., R], *args: Any, **kwargs: Any) -> Future[R]:
        # Log the submission
        func_name = getattr(func, "__name__", str(func))
        logger.debug(f"[ConcurrentFuturesInstrumentor] Submitting function: {func_name}")

        # The context propagation is handled by the initializer, so we can submit normally
        # But we can add additional logging or monitoring here if needed
        return original_submit(self, func, *args, **kwargs)

    return wrapped_submit


class ConcurrentFuturesInstrumentor(BaseInstrumentor):
    """
    Instrumentor for concurrent.futures module.

    This instrumentor patches ThreadPoolExecutor to automatically propagate
    OpenTelemetry context to worker threads, ensuring all LLM calls and other
    instrumented operations maintain proper trace context.
    """

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return a list of instrumentation dependencies."""
        return []

    def _instrument(self, **kwargs: Any) -> None:
        """Instrument the concurrent.futures module."""
        global _original_init, _original_submit

        logger.debug("[ConcurrentFuturesInstrumentor] Starting instrumentation")

        # Store original methods
        _original_init = ThreadPoolExecutor.__init__
        _original_submit = ThreadPoolExecutor.submit

        # Patch ThreadPoolExecutor methods
        ThreadPoolExecutor.__init__ = _context_propagating_init(_original_init)
        ThreadPoolExecutor.submit = _context_propagating_submit(_original_submit)

        logger.info("[ConcurrentFuturesInstrumentor] Successfully instrumented concurrent.futures.ThreadPoolExecutor")

    def _uninstrument(self, **kwargs: Any) -> None:
        """Uninstrument the concurrent.futures module."""
        global _original_init, _original_submit

        logger.debug("[ConcurrentFuturesInstrumentor] Starting uninstrumentation")

        # Restore original methods
        if _original_init:
            ThreadPoolExecutor.__init__ = _original_init
            _original_init = None

        if _original_submit:
            ThreadPoolExecutor.submit = _original_submit
            _original_submit = None

        logger.info("[ConcurrentFuturesInstrumentor] Successfully uninstrumented concurrent.futures.ThreadPoolExecutor")

    @staticmethod
    def instrument_module_directly() -> bool:
        """
        Directly instrument the module without using the standard instrumentor interface.

        This can be called manually if automatic instrumentation is not desired.

        Returns:
            bool: True if instrumentation was applied, False if already instrumented
        """
        instrumentor = ConcurrentFuturesInstrumentor()
        if not instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.instrument()
            return True
        return False

    @staticmethod
    def uninstrument_module_directly() -> bool:
        """
        Directly uninstrument the module.

        This can be called manually to remove instrumentation.

        Returns:
            bool: True if uninstrumentation was applied, False if already uninstrumented
        """
        instrumentor = ConcurrentFuturesInstrumentor()
        if instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.uninstrument()
            return True
        return False
