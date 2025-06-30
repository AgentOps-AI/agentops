"""
OpenTelemetry Instrumentation for concurrent.futures module.

This instrumentation automatically patches ThreadPoolExecutor to ensure proper
context propagation across thread boundaries, preventing "NEW TRACE DETECTED" issues.
"""

import contextvars
import functools
from typing import Any, Callable, Collection, Optional, Tuple, TypeVar, List, Dict

from concurrent.futures import ThreadPoolExecutor, Future

from agentops.instrumentation.common import CommonInstrumentor, InstrumentorConfig
from agentops.instrumentation.common.wrappers import WrapConfig
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

    return wrapped_init


def _context_propagating_submit(original_submit: Callable) -> Callable:
    """Wrap ThreadPoolExecutor.submit to ensure context propagation."""

    @functools.wraps(original_submit)
    def wrapped_submit(self: ThreadPoolExecutor, func: Callable[..., R], *args: Any, **kwargs: Any) -> Future[R]:
        # Log the submission
        func_name = getattr(func, "__name__", str(func))  # noqa: F841

        # The context propagation is handled by the initializer, so we can submit normally
        # But we can add additional logging or monitoring here if needed
        return original_submit(self, func, *args, **kwargs)

    return wrapped_submit


class ConcurrentFuturesInstrumentor(CommonInstrumentor):
    """
    Instrumentor for concurrent.futures module.

    This instrumentor patches ThreadPoolExecutor to automatically propagate
    OpenTelemetry context to worker threads, ensuring all LLM calls and other
    instrumented operations maintain proper trace context.
    """

    def __init__(self):
        """Initialize the concurrent.futures instrumentor."""
        config = InstrumentorConfig(
            library_name="agentops.instrumentation.concurrent_futures",
            library_version="0.1.0",
            wrapped_methods=[],  # We handle wrapping manually
            metrics_enabled=False,  # No metrics needed for context propagation
            dependencies=[],
        )
        super().__init__(config)
        self._original_init = None
        self._original_submit = None

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return a list of instrumentation dependencies."""
        return []

    def _get_wrapped_methods(self) -> List[WrapConfig]:
        """
        Return list of methods to be wrapped.

        For concurrent_futures, we don't use the standard wrapping mechanism
        since we're patching methods directly for context propagation.
        """
        return []

    def _create_metrics(self, meter) -> Dict[str, Any]:
        """
        Create metrics for this instrumentor.

        This instrumentor doesn't need metrics as it's purely for context propagation.

        Args:
            meter: The meter instance (unused)

        Returns:
            Empty dict since no metrics are needed
        """
        return {}

    def _instrument(self, **kwargs: Any) -> None:
        """Instrument the concurrent.futures module."""
        # Note: We don't call super()._instrument() here because we're not using
        # the standard wrapping mechanism for this special instrumentor

        logger.debug("[ConcurrentFuturesInstrumentor] Starting instrumentation")

        # Store original methods
        self._original_init = ThreadPoolExecutor.__init__
        self._original_submit = ThreadPoolExecutor.submit

        # Patch ThreadPoolExecutor methods
        ThreadPoolExecutor.__init__ = _context_propagating_init(self._original_init)
        ThreadPoolExecutor.submit = _context_propagating_submit(self._original_submit)

        logger.info("[ConcurrentFuturesInstrumentor] Successfully instrumented concurrent.futures.ThreadPoolExecutor")

    def _uninstrument(self, **kwargs: Any) -> None:
        """Uninstrument the concurrent.futures module."""
        # Note: We don't call super()._uninstrument() here because we're not using
        # the standard wrapping mechanism for this special instrumentor

        logger.debug("[ConcurrentFuturesInstrumentor] Starting uninstrumentation")

        # Restore original methods
        if self._original_init:
            ThreadPoolExecutor.__init__ = self._original_init
            self._original_init = None

        if self._original_submit:
            ThreadPoolExecutor.submit = self._original_submit
            self._original_submit = None

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
