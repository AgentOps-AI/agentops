from typing import Collection, List
from wrapt import wrap_function_wrapper

from agentops.instrumentation.common import BaseAgentOpsInstrumentor, StandardMetrics
from agentops.instrumentation.common.wrappers import WrapConfig
from agentops.logging import logger

# Import from refactored structure
from .memory import (
    mem0_add_wrapper,
    mem0_search_wrapper,
    mem0_get_all_wrapper,
    mem0_delete_wrapper,
    mem0_update_wrapper,
    mem0_get_wrapper,
    mem0_delete_all_wrapper,
    mem0_history_wrapper,
)

# Library info for tracer/meter
LIBRARY_NAME = "agentops.instrumentation.mem0"
LIBRARY_VERSION = "0.1.0"

# Methods to wrap for instrumentation using specialized wrappers
WRAPPER_METHODS = [
    # Sync Memory class methods
    {
        "package": "mem0.memory.main",
        "class_method": "Memory.add",
        "wrapper": mem0_add_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "Memory.search",
        "wrapper": mem0_search_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "Memory.get_all",
        "wrapper": mem0_get_all_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "Memory.get",
        "wrapper": mem0_get_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "Memory.delete",
        "wrapper": mem0_delete_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "Memory.delete_all",
        "wrapper": mem0_delete_all_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "Memory.update",
        "wrapper": mem0_update_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "Memory.history",
        "wrapper": mem0_history_wrapper,
    },
    # MemoryClient class methods
    {
        "package": "mem0.client.main",
        "class_method": "MemoryClient.add",
        "wrapper": mem0_add_wrapper,
    },
    {
        "package": "mem0.client.main",
        "class_method": "MemoryClient.search",
        "wrapper": mem0_search_wrapper,
    },
    {
        "package": "mem0.client.main",
        "class_method": "MemoryClient.get_all",
        "wrapper": mem0_get_all_wrapper,
    },
    {
        "package": "mem0.client.main",
        "class_method": "MemoryClient.get",
        "wrapper": mem0_get_wrapper,
    },
    {
        "package": "mem0.client.main",
        "class_method": "MemoryClient.delete",
        "wrapper": mem0_delete_wrapper,
    },
    {
        "package": "mem0.client.main",
        "class_method": "MemoryClient.delete_all",
        "wrapper": mem0_delete_all_wrapper,
    },
    {
        "package": "mem0.client.main",
        "class_method": "MemoryClient.update",
        "wrapper": mem0_update_wrapper,
    },
    # AsyncMemoryClient class methods
    {
        "package": "mem0.client.main",
        "class_method": "AsyncMemoryClient.add",
        "wrapper": mem0_add_wrapper,
    },
    {
        "package": "mem0.client.main",
        "class_method": "AsyncMemoryClient.search",
        "wrapper": mem0_search_wrapper,
    },
    {
        "package": "mem0.client.main",
        "class_method": "AsyncMemoryClient.get_all",
        "wrapper": mem0_get_all_wrapper,
    },
    {
        "package": "mem0.client.main",
        "class_method": "AsyncMemoryClient.get",
        "wrapper": mem0_get_wrapper,
    },
    {
        "package": "mem0.client.main",
        "class_method": "AsyncMemoryClient.delete",
        "wrapper": mem0_delete_wrapper,
    },
    {
        "package": "mem0.client.main",
        "class_method": "AsyncMemoryClient.delete_all",
        "wrapper": mem0_delete_all_wrapper,
    },
    {
        "package": "mem0.client.main",
        "class_method": "AsyncMemoryClient.update",
        "wrapper": mem0_update_wrapper,
    },
    # AsyncMemory class methods
    {
        "package": "mem0.memory.main",
        "class_method": "AsyncMemory.add",
        "wrapper": mem0_add_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "AsyncMemory.search",
        "wrapper": mem0_search_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "AsyncMemory.get_all",
        "wrapper": mem0_get_all_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "AsyncMemory.get",
        "wrapper": mem0_get_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "AsyncMemory.delete",
        "wrapper": mem0_delete_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "AsyncMemory.delete_all",
        "wrapper": mem0_delete_all_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "AsyncMemory.update",
        "wrapper": mem0_update_wrapper,
    },
    {
        "package": "mem0.memory.main",
        "class_method": "AsyncMemory.history",
        "wrapper": mem0_history_wrapper,
    },
]


class Mem0Instrumentor(BaseAgentOpsInstrumentor):
    """An instrumentor for Mem0's client library.

    This class provides instrumentation for Mem0's memory operations by wrapping key methods
    in the Memory, AsyncMemory, MemoryClient, and AsyncMemoryClient classes. It captures
    telemetry data for memory operations including add, search, get, delete, delete_all,
    update, and history operations.

    The instrumentor gracefully handles missing optional dependencies - if a provider's
    package is not installed, it will be skipped without causing errors.

    It captures metrics including operation duration, memory counts, and exceptions.
    """

    def __init__(self):
        """Initialize the Mem0 instrumentor."""
        super().__init__(
            name="mem0",
            version=LIBRARY_VERSION,
            library_name=LIBRARY_NAME,
        )

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation.

        Returns:
            A collection of package specifications required for this instrumentation.
        """
        return ["mem0ai >= 0.1.10"]

    def _get_wrapped_methods(self) -> List[WrapConfig]:
        """Return list of methods to be wrapped.

        For Mem0, we don't use the standard wrapping mechanism
        since we're using specialized wrappers instead.
        """
        return []

    def _instrument(self, **kwargs):
        """Instrument the Mem0 Memory API.

        This method wraps the key methods in the Mem0 Memory client to capture
        telemetry data for memory operations. It sets up tracers, meters, and wraps the
        appropriate methods for instrumentation.

        Args:
            **kwargs: Configuration options for instrumentation.
        """
        # Note: We don't call super()._instrument() here because we're not using
        # the standard wrapping mechanism for this special instrumentor

        logger.debug("Starting Mem0 instrumentation...")

        # Get tracer and meter from base class properties
        self._tracer_provider = kwargs.get("tracer_provider")
        self._meter_provider = kwargs.get("meter_provider")

        # Initialize tracer and meter (these are set by base class properties)
        tracer = self._tracer
        meter = self._meter

        # Create standard metrics for memory operations
        self._metrics = StandardMetrics(meter)
        self._metrics.create_llm_metrics(system_name="Mem0", operation_description="Mem0 memory operation")

        # Create additional metrics specific to memory operations
        meter.create_histogram(
            name="mem0.memory.count",
            unit="memory",
            description="Number of memories processed in Mem0 operations",
        )

        # Use specialized wrappers that ensure proper context hierarchy
        for method_config in WRAPPER_METHODS:
            try:
                package = method_config["package"]
                class_method = method_config["class_method"]
                wrapper_func = method_config["wrapper"]
                wrap_function_wrapper(package, class_method, wrapper_func(tracer))
            except (AttributeError, ModuleNotFoundError) as e:
                # Use debug level for missing optional packages instead of error
                # since LLM providers are optional dependencies
                logger.debug(f"Skipping {package}.{class_method} - package not installed: {e}")
            except Exception as e:
                # Log unexpected errors as warnings
                logger.warning(f"Unexpected error wrapping {package}.{class_method}: {e}")

        logger.info("Mem0 instrumentation enabled")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from Mem0 Memory API.

        This method unwraps all methods that were wrapped during instrumentation,
        restoring the original behavior of the Mem0 Memory API.

        Args:
            **kwargs: Configuration options for uninstrumentation.
        """
        # Note: We don't call super()._uninstrument() here because we're not using
        # the standard wrapping mechanism for this special instrumentor

        # Unwrap specialized methods
        from opentelemetry.instrumentation.utils import unwrap

        for method_config in WRAPPER_METHODS:
            try:
                package = method_config["package"]
                class_method = method_config["class_method"]
                unwrap(package, class_method)
            except Exception as e:
                logger.debug(f"Failed to unwrap {package}.{class_method}: {e}")

        logger.info("Mem0 instrumentation disabled")
