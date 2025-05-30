from __future__ import annotations

import atexit
import threading
import platform
import sys
import os
import psutil
from typing import Optional, Any, Dict

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, Span
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry import context as context_api

from agentops.exceptions import AgentOpsClientNotInitializedException
from agentops.logging import logger, setup_print_logger
from agentops.sdk.processors import InternalSpanProcessor
from agentops.sdk.types import TracingConfig
from agentops.semconv import ResourceAttributes, SpanKind, SpanAttributes, CoreAttributes
from agentops.helpers.dashboard import log_trace_url

# No need to create shortcuts since we're using our own ResourceAttributes class now


# Define TraceContext to hold span and token
class TraceContext:
    def __init__(self, span: Span, token: Optional[context_api.Token] = None, is_init_trace: bool = False):
        self.span = span
        self.token = token
        self.is_init_trace = is_init_trace  # Flag to identify the auto-started trace


def get_imported_libraries():
    """
    Get the top-level imported libraries in the current script.

    Returns:
        list: List of imported libraries
    """
    user_libs = []

    builtin_modules = {
        "builtins",
        "sys",
        "os",
        "_thread",
        "abc",
        "io",
        "re",
        "types",
        "collections",
        "enum",
        "math",
        "datetime",
        "time",
        "warnings",
    }

    try:
        main_module = sys.modules.get("__main__")
        if main_module and hasattr(main_module, "__dict__"):
            for name, obj in main_module.__dict__.items():
                if isinstance(obj, type(sys)) and hasattr(obj, "__name__"):
                    mod_name = obj.__name__.split(".")[0]
                    if mod_name and not mod_name.startswith("_") and mod_name not in builtin_modules:
                        user_libs.append(mod_name)
    except Exception as e:
        logger.debug(f"Error getting imports: {e}")

    return user_libs


def get_system_stats():
    """
    Get basic system stats including CPU and memory information.

    Returns:
        dict: Dictionary with system information
    """
    system_info = {
        ResourceAttributes.HOST_MACHINE: platform.machine(),
        ResourceAttributes.HOST_NAME: platform.node(),
        ResourceAttributes.HOST_NODE: platform.node(),
        ResourceAttributes.HOST_PROCESSOR: platform.processor(),
        ResourceAttributes.HOST_SYSTEM: platform.system(),
        ResourceAttributes.HOST_VERSION: platform.version(),
        ResourceAttributes.HOST_OS_RELEASE: platform.release(),
    }

    # Add CPU stats
    try:
        system_info[ResourceAttributes.CPU_COUNT] = os.cpu_count() or 0
        system_info[ResourceAttributes.CPU_PERCENT] = psutil.cpu_percent(interval=0.1)
    except Exception as e:
        logger.debug(f"Error getting CPU stats: {e}")

    # Add memory stats
    try:
        memory = psutil.virtual_memory()
        system_info[ResourceAttributes.MEMORY_TOTAL] = memory.total
        system_info[ResourceAttributes.MEMORY_AVAILABLE] = memory.available
        system_info[ResourceAttributes.MEMORY_USED] = memory.used
        system_info[ResourceAttributes.MEMORY_PERCENT] = memory.percent
    except Exception as e:
        logger.debug(f"Error getting memory stats: {e}")

    return system_info


def setup_telemetry(
    service_name: str = "agentops",
    project_id: Optional[str] = None,
    exporter_endpoint: str = "https://otlp.agentops.ai/v1/traces",
    metrics_endpoint: str = "https://otlp.agentops.ai/v1/metrics",
    max_queue_size: int = 512,
    max_wait_time: int = 5000,
    export_flush_interval: int = 1000,
    jwt: Optional[str] = None,
) -> tuple[TracerProvider, MeterProvider]:
    """
    Setup the telemetry system.

    Args:
        service_name: Name of the OpenTelemetry service
        project_id: Project ID to include in resource attributes
        exporter_endpoint: Endpoint for the span exporter
        metrics_endpoint: Endpoint for the metrics exporter
        max_queue_size: Maximum number of spans to queue before forcing a flush
        max_wait_time: Maximum time in milliseconds to wait before flushing
        export_flush_interval: Time interval in milliseconds between automatic exports of telemetry data
        jwt: JWT token for authentication

    Returns:
        Tuple of (TracerProvider, MeterProvider)
    """
    # Create resource attributes dictionary
    resource_attrs = {ResourceAttributes.SERVICE_NAME: service_name}

    # Add project_id to resource attributes if available
    if project_id:
        # Add project_id as a custom resource attribute
        resource_attrs[ResourceAttributes.PROJECT_ID] = project_id
        logger.debug(f"Including project_id in resource attributes: {project_id}")

    # Add system information
    system_stats = get_system_stats()
    resource_attrs.update(system_stats)

    # Add imported libraries
    imported_libraries = get_imported_libraries()
    resource_attrs[ResourceAttributes.IMPORTED_LIBRARIES] = imported_libraries

    resource = Resource(resource_attrs)
    provider = TracerProvider(resource=resource)

    # Set as global provider
    trace.set_tracer_provider(provider)

    # Create exporter with authentication
    exporter = OTLPSpanExporter(endpoint=exporter_endpoint, headers={"Authorization": f"Bearer {jwt}"} if jwt else {})

    # Regular processor for normal spans and immediate export
    processor = BatchSpanProcessor(
        exporter,
        max_export_batch_size=max_queue_size,
        schedule_delay_millis=export_flush_interval,
    )
    provider.add_span_processor(processor)
    internal_processor = InternalSpanProcessor()  # Catches spans for AgentOps on-terminal printing
    provider.add_span_processor(internal_processor)

    # Setup metrics
    metric_exporter = OTLPMetricExporter(
        endpoint=metrics_endpoint, headers={"Authorization": f"Bearer {jwt}"} if jwt else {}
    )
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    ### Logging
    setup_print_logger()

    # Initialize root context
    # context_api.get_current() # It's better to manage context explicitly with traces

    logger.debug("Telemetry system initialized")

    return provider, meter_provider


class TracingCore:
    """
    Central component for tracing in AgentOps.

    This class manages the creation, processing, and export of spans.
    It handles provider management, span creation, and context propagation.
    """

    _instance: Optional[TracingCore] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> TracingCore:
        """Get the singleton instance of TracingCore."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize the tracing core."""
        self._provider: Optional[TracerProvider] = None
        self._meter_provider: Optional[MeterProvider] = None
        self._initialized = False
        self._config: Optional[TracingConfig] = None
        self._span_processors: list = []
        self._active_traces: dict = {}
        self._traces_lock = threading.Lock()

        # Register shutdown handler
        atexit.register(self.shutdown)

    def initialize(self, jwt: Optional[str] = None, **kwargs: Any) -> None:
        """
        Initialize the tracing core with the given configuration.

        Args:
            jwt: JWT token for authentication
            **kwargs: Configuration parameters for tracing
                service_name: Name of the service
                exporter: Custom span exporter
                processor: Custom span processor
                exporter_endpoint: Endpoint for the span exporter
                max_queue_size: Maximum number of spans to queue before forcing a flush
                max_wait_time: Maximum time in milliseconds to wait before flushing
                api_key: API key for authentication (required for authenticated exporter)
                project_id: Project ID to include in resource attributes
        """
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            # Set default values for required fields
            kwargs.setdefault("service_name", "agentops")
            kwargs.setdefault("exporter_endpoint", "https://otlp.agentops.ai/v1/traces")
            kwargs.setdefault("metrics_endpoint", "https://otlp.agentops.ai/v1/metrics")
            kwargs.setdefault("max_queue_size", 512)
            kwargs.setdefault("max_wait_time", 5000)
            kwargs.setdefault("export_flush_interval", 1000)

            # Create a TracingConfig from kwargs with proper defaults
            config: TracingConfig = {
                "service_name": kwargs["service_name"],
                "exporter_endpoint": kwargs["exporter_endpoint"],
                "metrics_endpoint": kwargs["metrics_endpoint"],
                "max_queue_size": kwargs["max_queue_size"],
                "max_wait_time": kwargs["max_wait_time"],
                "export_flush_interval": kwargs["export_flush_interval"],
                "api_key": kwargs.get("api_key"),
                "project_id": kwargs.get("project_id"),
            }

            self._config = config

            # Setup telemetry using the extracted configuration
            provider, meter_provider = setup_telemetry(
                service_name=config["service_name"] or "",
                project_id=config.get("project_id"),
                exporter_endpoint=config["exporter_endpoint"],
                metrics_endpoint=config["metrics_endpoint"],
                max_queue_size=config["max_queue_size"],
                max_wait_time=config["max_wait_time"],
                export_flush_interval=config["export_flush_interval"],
                jwt=jwt,
            )

            self._provider = provider
            self._meter_provider = meter_provider

            self._initialized = True
            logger.debug("Tracing core initialized")

    @property
    def initialized(self) -> bool:
        """Check if the tracing core is initialized."""
        return self._initialized

    @property
    def config(self) -> TracingConfig:
        """Get the tracing configuration."""
        if self._config is None:
            # This case should ideally not be reached if initialized properly
            raise AgentOpsClientNotInitializedException("TracingCore config accessed before initialization.")
        return self._config

    def shutdown(self) -> None:
        """Shutdown the tracing core."""

        with self._lock:
            if not self._initialized or not self._provider:
                return

            logger.debug("Attempting to flush span processors during shutdown...")
            self._flush_span_processors()

            # Shutdown provider
            try:
                self._provider.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down provider: {e}")

            # Shutdown meter_provider
            if hasattr(self, "_meter_provider") and self._meter_provider:
                try:
                    self._meter_provider.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down meter provider: {e}")

            self._initialized = False
            logger.debug("Tracing core shut down")

    def _flush_span_processors(self) -> None:
        """Helper to force flush all span processors."""
        if not self._provider or not hasattr(self._provider, "force_flush"):
            logger.debug("No provider or provider cannot force_flush.")
            return

        try:
            self._provider.force_flush()  # type: ignore
            logger.debug("Provider force_flush completed.")
        except Exception as e:
            logger.warning(f"Failed to force flush provider's span processors: {e}", exc_info=True)

    def get_tracer(self, name: str = "agentops") -> trace.Tracer:
        """
        Get a tracer with the given name.

        Args:
            name: Name of the tracer

        Returns:
            A tracer with the given name
        """
        if not self._initialized:
            raise AgentOpsClientNotInitializedException

        return trace.get_tracer(name)

    @classmethod
    def initialize_from_config(cls, config_obj: Any, **kwargs: Any) -> None:
        """
        Initialize the tracing core from a configuration object.

        Args:
            config: Configuration object (dict or object with dict method)
            **kwargs: Additional keyword arguments to pass to initialize
        """
        instance = cls.get_instance()

        # Extract tracing-specific configuration
        # For TracingConfig, we can directly pass it to initialize
        if isinstance(config_obj, dict):
            # If it's already a dict (TracingConfig), use it directly
            tracing_kwargs = config_obj.copy()
        else:
            # For backward compatibility with old Config object
            # Extract tracing-specific configuration from the Config object
            # Use getattr with default values to ensure we don't pass None for required fields
            tracing_kwargs = {
                k: v
                for k, v in {
                    "exporter": getattr(config_obj, "exporter", None),
                    "processor": getattr(config_obj, "processor", None),
                    "exporter_endpoint": getattr(config_obj, "exporter_endpoint", None),
                    "max_queue_size": getattr(config_obj, "max_queue_size", 512),
                    "max_wait_time": getattr(config_obj, "max_wait_time", 5000),
                    "export_flush_interval": getattr(config_obj, "export_flush_interval", 1000),
                    "api_key": getattr(config_obj, "api_key", None),
                    "project_id": getattr(config_obj, "project_id", None),
                    "endpoint": getattr(config_obj, "endpoint", None),
                }.items()
                if v is not None
            }
        # Update with any additional kwargs
        tracing_kwargs.update(kwargs)

        # Initialize with the extracted configuration
        instance.initialize(**tracing_kwargs)

        # Span types are registered in the constructor
        # No need to register them here anymore

    def start_trace(
        self, trace_name: str = "session", tags: Optional[dict | list] = None, is_init_trace: bool = False
    ) -> Optional[TraceContext]:
        """
        Starts a new trace (root span) and returns its context.

        Args:
            trace_name: Name for the trace (e.g., "session", "my_custom_trace").
            tags: Optional tags to attach to the trace span.
            is_init_trace: Internal flag to mark if this is the automatically started init trace.

        Returns:
            A TraceContext object containing the span and context token, or None if not initialized.
        """
        if not self.initialized:
            logger.warning("TracingCore not initialized. Cannot start trace.")
            return None

        from agentops.sdk.decorators.utility import _make_span  # Local import

        attributes: dict = {}
        if tags:
            if isinstance(tags, list):
                attributes[CoreAttributes.TAGS] = tags
            elif isinstance(tags, dict):
                attributes.update(tags)  # Add dict tags directly
            else:
                logger.warning(f"Invalid tags format: {tags}. Must be list or dict.")

        # _make_span creates and starts the span, and activates it in the current context
        # It returns: span, context_object, context_token
        span, _, context_token = _make_span(trace_name, span_kind=SpanKind.SESSION, attributes=attributes)
        logger.debug(f"Trace '{trace_name}' started with span ID: {span.get_span_context().span_id}")

        # Log the session replay URL for this new trace
        try:
            log_trace_url(span, title=trace_name)
        except Exception as e:
            logger.warning(f"Failed to log trace URL for '{trace_name}': {e}")

        trace_context = TraceContext(span, token=context_token, is_init_trace=is_init_trace)

        # Track the active trace
        with self._traces_lock:
            try:
                trace_id = f"{span.get_span_context().trace_id:x}"
            except (TypeError, ValueError):
                # Handle case where span is mocked or trace_id is not a valid integer
                trace_id = str(span.get_span_context().trace_id)
            self._active_traces[trace_id] = trace_context
            logger.debug(f"Added trace {trace_id} to active traces. Total active: {len(self._active_traces)}")

        return trace_context

    def end_trace(self, trace_context: Optional[TraceContext] = None, end_state: str = "Success") -> None:
        """
        Ends a trace (its root span) and finalizes it.
        If no trace_context is provided, ends all active session spans.

        Args:
            trace_context: The TraceContext object returned by start_trace. If None, ends all active traces.
            end_state: The final state of the trace (e.g., "Success", "Failure", "Error").
        """
        if not self.initialized:
            logger.warning("TracingCore not initialized. Cannot end trace.")
            return

        # If no specific trace_context provided, end all active traces
        if trace_context is None:
            with self._traces_lock:
                active_traces = list(self._active_traces.values())
                logger.debug(f"Ending all {len(active_traces)} active traces with state: {end_state}")

            for active_trace in active_traces:
                self._end_single_trace(active_trace, end_state)
            return

        # End specific trace
        self._end_single_trace(trace_context, end_state)

    def _end_single_trace(self, trace_context: TraceContext, end_state: str) -> None:
        """
        Internal method to end a single trace.

        Args:
            trace_context: The TraceContext object to end.
            end_state: The final state of the trace.
        """
        from agentops.sdk.decorators.utility import _finalize_span  # Local import

        if not trace_context or not trace_context.span:
            logger.warning("Invalid TraceContext or span provided to end trace.")
            return

        span = trace_context.span
        token = trace_context.token
        try:
            trace_id = f"{span.get_span_context().trace_id:x}"
        except (TypeError, ValueError):
            # Handle case where span is mocked or trace_id is not a valid integer
            trace_id = str(span.get_span_context().trace_id)

        logger.debug(f"Ending trace with span ID: {span.get_span_context().span_id}, end_state: {end_state}")

        try:
            span.set_attribute(SpanAttributes.AGENTOPS_SESSION_END_STATE, end_state)
            _finalize_span(span, token=token)

            # Remove from active traces
            with self._traces_lock:
                if trace_id in self._active_traces:
                    del self._active_traces[trace_id]
                    logger.debug(f"Removed trace {trace_id} from active traces. Remaining: {len(self._active_traces)}")

            # For root spans (traces), we might want an immediate flush after they end.
            self._flush_span_processors()

            # Log the session replay URL again after the trace has ended
            # The span object should still contain the necessary context (trace_id)
            try:
                # Use span.name as the title, which should reflect the original trace_name
                log_trace_url(span, title=span.name)
            except Exception as e:
                logger.warning(f"Failed to log trace URL after ending trace '{span.name}': {e}")

        except Exception as e:
            logger.error(f"Error ending trace: {e}", exc_info=True)

    def get_active_traces(self) -> Dict[str, TraceContext]:
        """
        Get a copy of currently active traces.

        Returns:
            Dictionary mapping trace IDs to TraceContext objects.
        """
        with self._traces_lock:
            return self._active_traces.copy()

    def get_active_trace_count(self) -> int:
        """
        Get the number of currently active traces.

        Returns:
            Number of active traces.
        """
        with self._traces_lock:
            return len(self._active_traces)
