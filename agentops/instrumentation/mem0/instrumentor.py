from typing import Collection
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer
from opentelemetry.metrics import get_meter
from wrapt import wrap_function_wrapper

from agentops.instrumentation.mem0 import LIBRARY_NAME, LIBRARY_VERSION
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

from agentops.semconv import Meters

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


class Mem0Instrumentor(BaseInstrumentor):
    """An instrumentor for Mem0's client library.

    This class provides instrumentation for Mem0's memory operations by wrapping key methods
    in the Memory, AsyncMemory, MemoryClient, and AsyncMemoryClient classes. It captures
    telemetry data for memory operations including add, search, get, delete, delete_all,
    update, and history operations.

    The instrumentor gracefully handles missing optional dependencies - if a provider's
    package is not installed, it will be skipped without causing errors.

    It captures metrics including operation duration, memory counts, and exceptions.
    """

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation.

        Returns:
            A collection of package specifications required for this instrumentation.
        """
        return ["mem0ai >= 0.1.10"]

    def _instrument(self, **kwargs):
        """Instrument the Mem0 Memory API.

        This method wraps the key methods in the Mem0 Memory client to capture
        telemetry data for memory operations. It sets up tracers, meters, and wraps the
        appropriate methods for instrumentation.

        Args:
            **kwargs: Configuration options for instrumentation.
        """
        super()._instrument(**kwargs)
        logger.debug("Starting Mem0 instrumentation...")

        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider)

        meter_provider = kwargs.get("meter_provider")
        meter = get_meter(LIBRARY_NAME, LIBRARY_VERSION, meter_provider)

        # Create metrics for memory operations
        meter.create_histogram(
            name=Meters.LLM_OPERATION_DURATION,
            unit="s",
            description="Mem0 memory operation duration",
        )

        meter.create_counter(
            name=Meters.LLM_COMPLETIONS_EXCEPTIONS,
            unit="time",
            description="Number of exceptions occurred during Mem0 operations",
        )

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
        logger.debug("Mem0 instrumentation completed")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from Mem0 Memory API.

        This method unwraps all methods that were wrapped during instrumentation,
        restoring the original behavior of the Mem0 Memory API.

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
