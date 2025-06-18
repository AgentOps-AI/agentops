from typing import Dict, Any
from wrapt import wrap_function_wrapper
from opentelemetry.metrics import Meter

from agentops.instrumentation.common import CommonInstrumentor, StandardMetrics, InstrumentorConfig
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


class Mem0Instrumentor(CommonInstrumentor):
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
        config = InstrumentorConfig(
            library_name=LIBRARY_NAME,
            library_version=LIBRARY_VERSION,
            wrapped_methods=[],  # We use custom wrapping for Mem0
            metrics_enabled=True,
            dependencies=["mem0ai >= 0.1.10"],
        )
        super().__init__(config)

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create metrics for Mem0 operations.

        Args:
            meter: The OpenTelemetry meter to use for creating metrics.

        Returns:
            Dictionary containing the created metrics.
        """
        metrics = StandardMetrics.create_standard_metrics(meter)

        # Add Mem0-specific memory count metric
        metrics["memory_count_histogram"] = meter.create_histogram(
            name="mem0.memory.count",
            unit="memory",
            description="Number of memories processed in Mem0 operations",
        )

        return metrics

    def _custom_wrap(self, **kwargs):
        """Perform custom wrapping for Mem0 methods.

        Args:
            **kwargs: Configuration options for instrumentation.
        """
        logger.debug("Starting Mem0 instrumentation...")

        # Use specialized wrappers that ensure proper context hierarchy
        for method_config in WRAPPER_METHODS:
            try:
                package = method_config["package"]
                class_method = method_config["class_method"]
                wrapper_func = method_config["wrapper"]
                wrap_function_wrapper(package, class_method, wrapper_func(self._tracer))
            except (AttributeError, ModuleNotFoundError) as e:
                # Use debug level for missing optional packages instead of error
                # since LLM providers are optional dependencies
                logger.debug(f"Skipping {package}.{class_method} - package not installed: {e}")
            except Exception as e:
                # Log unexpected errors as warnings
                logger.warning(f"Unexpected error wrapping {package}.{class_method}: {e}")

        logger.info("Mem0 instrumentation enabled")

    def _custom_unwrap(self, **kwargs):
        """Remove custom wrapping for Mem0 methods.

        Args:
            **kwargs: Configuration options for uninstrumentation.
        """
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
