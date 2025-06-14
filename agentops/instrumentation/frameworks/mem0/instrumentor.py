from typing import Collection
from opentelemetry.trace import get_tracer

from agentops.instrumentation.common.base_instrumentor import AgentOpsBaseInstrumentor
from agentops.instrumentation.common.config import WrapConfig
from agentops.instrumentation.frameworks.mem0 import LIBRARY_NAME, LIBRARY_VERSION
from agentops.logging import logger

# Import from refactored structure
from .memory import (
    get_add_attributes,
    get_search_attributes,
    get_get_all_attributes,
    get_delete_attributes,
    get_update_attributes,
    get_get_attributes,
    get_delete_all_attributes,
    get_history_attributes,
)


# Methods to wrap for instrumentation using specialized wrappers
WRAPPER_METHODS = [
    # Sync Memory class methods
    WrapConfig(
        module="mem0.memory.main",
        object="Memory",
        method="add",
        span_name="mem0.memory.add",
        extract_attributes=get_add_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="Memory",
        method="search",
        span_name="mem0.memory.search",
        extract_attributes=get_search_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="Memory",
        method="get_all",
        span_name="mem0.memory.get_all",
        extract_attributes=get_get_all_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="Memory",
        method="get",
        span_name="mem0.memory.get",
        extract_attributes=get_get_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="Memory",
        method="delete",
        span_name="mem0.memory.delete",
        extract_attributes=get_delete_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="Memory",
        method="delete_all",
        span_name="mem0.memory.delete_all",
        extract_attributes=get_delete_all_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="Memory",
        method="update",
        span_name="mem0.memory.update",
        extract_attributes=get_update_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="Memory",
        method="history",
        span_name="mem0.memory.history",
        extract_attributes=get_history_attributes,
    ),
    # MemoryClient class methods
    WrapConfig(
        module="mem0.client.main",
        object="MemoryClient",
        method="add",
        span_name="mem0.memory.add",
        extract_attributes=get_add_attributes,
    ),
    WrapConfig(
        module="mem0.client.main",
        object="MemoryClient",
        method="search",
        span_name="mem0.memory.search",
        extract_attributes=get_search_attributes,
    ),
    WrapConfig(
        module="mem0.client.main",
        object="MemoryClient",
        method="get_all",
        span_name="mem0.memory.get_all",
        extract_attributes=get_get_all_attributes,
    ),
    WrapConfig(
        module="mem0.client.main",
        object="MemoryClient",
        method="get",
        span_name="mem0.memory.get",
        extract_attributes=get_get_attributes,
    ),
    WrapConfig(
        module="mem0.client.main",
        object="MemoryClient",
        method="delete",
        span_name="mem0.memory.delete",
        extract_attributes=get_delete_attributes,
    ),
    WrapConfig(
        module="mem0.client.main",
        object="MemoryClient",
        method="delete_all",
        span_name="mem0.memory.delete_all",
        extract_attributes=get_delete_all_attributes,
    ),
    WrapConfig(
        module="mem0.client.main",
        object="MemoryClient",
        method="update",
        span_name="mem0.memory.update",
        extract_attributes=get_update_attributes,
    ),
    # AsyncMemoryClient class methods
    WrapConfig(
        module="mem0.client.main",
        object="AsyncMemoryClient",
        method="add",
        span_name="mem0.AsyncMemory.add",
        extract_attributes=get_add_attributes,
    ),
    WrapConfig(
        module="mem0.client.main",
        object="AsyncMemoryClient",
        method="search",
        span_name="mem0.AsyncMemory.search",
        extract_attributes=get_search_attributes,
    ),
    WrapConfig(
        module="mem0.client.main",
        object="AsyncMemoryClient",
        method="get_all",
        span_name="mem0.AsyncMemory.get_all",
        extract_attributes=get_get_all_attributes,
    ),
    WrapConfig(
        module="mem0.client.main",
        object="AsyncMemoryClient",
        method="get",
        span_name="mem0.AsyncMemory.get",
        extract_attributes=get_get_attributes,
    ),
    WrapConfig(
        module="mem0.client.main",
        object="AsyncMemoryClient",
        method="delete",
        span_name="mem0.AsyncMemory.delete",
        extract_attributes=get_delete_attributes,
    ),
    WrapConfig(
        module="mem0.client.main",
        object="AsyncMemoryClient",
        method="delete_all",
        span_name="mem0.AsyncMemory.delete_all",
        extract_attributes=get_delete_all_attributes,
    ),
    WrapConfig(
        module="mem0.client.main",
        object="AsyncMemoryClient",
        method="update",
        span_name="mem0.AsyncMemory.update",
        extract_attributes=get_update_attributes,
    ),
    # AsyncMemory class methods
    WrapConfig(
        module="mem0.memory.main",
        object="AsyncMemory",
        method="add",
        span_name="mem0.AsyncMemory.add",
        extract_attributes=get_add_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="AsyncMemory",
        method="search",
        span_name="mem0.AsyncMemory.search",
        extract_attributes=get_search_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="AsyncMemory",
        method="get_all",
        span_name="mem0.AsyncMemory.get_all",
        extract_attributes=get_get_all_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="AsyncMemory",
        method="get",
        span_name="mem0.AsyncMemory.get",
        extract_attributes=get_get_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="AsyncMemory",
        method="delete",
        span_name="mem0.AsyncMemory.delete",
        extract_attributes=get_delete_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="AsyncMemory",
        method="delete_all",
        span_name="mem0.AsyncMemory.delete_all",
        extract_attributes=get_delete_all_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="AsyncMemory",
        method="update",
        span_name="mem0.AsyncMemory.update",
        extract_attributes=get_update_attributes,
    ),
    WrapConfig(
        module="mem0.memory.main",
        object="AsyncMemory",
        method="history",
        span_name="mem0.AsyncMemory.history",
        extract_attributes=get_history_attributes,
    ),
]


class Mem0Instrumentor(AgentOpsBaseInstrumentor):
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

    def get_library_name(self) -> str:
        """Return the library name for this instrumentor."""
        return LIBRARY_NAME

    def get_library_version(self) -> str:
        """Return the library version for this instrumentor."""
        return LIBRARY_VERSION

    def _init_custom_metrics(self):
        """Initialize custom metrics specific to mem0."""
        self.add_custom_metric(
            name="mem0.memory.count",
            metric_type="histogram",
            unit="memory",
            description="Number of memories processed in Mem0 operations",
        )

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

        # Use base class method to wrap all configured methods
        self._wrap_methods(WRAPPER_METHODS, tracer)

        logger.debug("Mem0 instrumentation completed")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from Mem0 Memory API.

        This method unwraps all methods that were wrapped during instrumentation,
        restoring the original behavior of the Mem0 Memory API.

        Args:
            **kwargs: Configuration options for uninstrumentation.
        """
        # Use base class method to unwrap all configured methods
        self._unwrap_methods(WRAPPER_METHODS)
