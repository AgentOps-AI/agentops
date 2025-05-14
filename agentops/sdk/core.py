from __future__ import annotations

import atexit
import threading
import platform
import sys
import os
import psutil
from typing import Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry import context as context_api

from agentops.exceptions import AgentOpsClientNotInitializedException
from agentops.logging import logger, setup_print_logger
from agentops.sdk.processors import InternalSpanProcessor
from agentops.sdk.types import TracingConfig
from agentops.semconv import ResourceAttributes

# No need to create shortcuts since we're using our own ResourceAttributes class now


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
    provider.add_span_processor(InternalSpanProcessor())  # Catches spans for AgentOps on-terminal printing

    # Setup metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=metrics_endpoint, headers={"Authorization": f"Bearer {jwt}"} if jwt else {})
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    ### Logging
    setup_print_logger()

    # Initialize root context
    context_api.get_current()

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
        self._provider = None
        self._initialized = False
        self._config = None

        # Register shutdown handler
        atexit.register(self.shutdown)

    def initialize(self, jwt: Optional[str] = None, **kwargs) -> None:
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
            self._provider, self._meter_provider = setup_telemetry(
                service_name=config["service_name"] or "",
                project_id=config.get("project_id"),
                exporter_endpoint=config["exporter_endpoint"],
                metrics_endpoint=config["metrics_endpoint"],
                max_queue_size=config["max_queue_size"],
                max_wait_time=config["max_wait_time"],
                export_flush_interval=config["export_flush_interval"],
                jwt=jwt,
            )

            self._initialized = True
            logger.debug("Tracing core initialized")

    @property
    def initialized(self) -> bool:
        """Check if the tracing core is initialized."""
        return self._initialized

    @property
    def config(self) -> TracingConfig:
        """Get the tracing configuration."""
        return self._config  # type: ignore

    def shutdown(self) -> None:
        """Shutdown the tracing core."""

        with self._lock:
            # Perform a single flush on the SynchronousSpanProcessor (which takes care of all processors' shutdown)
            if not self._initialized:
                return
            self._provider._active_span_processor.force_flush(self.config["max_wait_time"])  # type: ignore

            # Shutdown provider
            if self._provider:
                try:
                    self._provider.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down provider: {e}")

            self._initialized = False

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
    def initialize_from_config(cls, config, **kwargs):
        """
        Initialize the tracing core from a configuration object.

        Args:
            config: Configuration object (dict or object with dict method)
            **kwargs: Additional keyword arguments to pass to initialize
        """
        instance = cls.get_instance()

        # Extract tracing-specific configuration
        # For TracingConfig, we can directly pass it to initialize
        if isinstance(config, dict):
            # If it's already a dict (TracingConfig), use it directly
            tracing_kwargs = config.copy()
        else:
            # For backward compatibility with old Config object
            # Extract tracing-specific configuration from the Config object
            # Use getattr with default values to ensure we don't pass None for required fields
            tracing_kwargs = {
                k: v
                for k, v in {
                    "exporter": getattr(config, "exporter", None),
                    "processor": getattr(config, "processor", None),
                    "exporter_endpoint": getattr(config, "exporter_endpoint", None),
                    "max_queue_size": getattr(config, "max_queue_size", 512),
                    "max_wait_time": getattr(config, "max_wait_time", 5000),
                    "export_flush_interval": getattr(config, "export_flush_interval", 1000),
                    "api_key": getattr(config, "api_key", None),
                    "project_id": getattr(config, "project_id", None),
                    "endpoint": getattr(config, "endpoint", None),
                }.items()
                if v is not None
            }
        # Update with any additional kwargs
        tracing_kwargs.update(kwargs)

        # Initialize with the extracted configuration
        instance.initialize(**tracing_kwargs)

        # Span types are registered in the constructor
        # No need to register them here anymore
