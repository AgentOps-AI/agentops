from __future__ import annotations

import atexit
import threading
from typing import Any, Dict, List, Optional, Set, Type, Union, cast

from opentelemetry import context, metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter
from opentelemetry.trace import Span

from agentops.exceptions import AgentOpsClientNotInitializedException
from agentops.logging import logger
from agentops.sdk.exporters import AuthenticatedOTLPExporter
from agentops.sdk.processors import InternalSpanProcessor
from agentops.sdk.types import TracingConfig
from agentops.semconv import ResourceAttributes
from agentops.semconv.core import CoreAttributes

# No need to create shortcuts since we're using our own ResourceAttributes class now


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
        self._processors: List[SpanProcessor] = []
        self._initialized = False
        self._config = None

        # Register shutdown handler
        atexit.register(self.shutdown)

    def initialize(self, jwt: Optional[str] = None, **kwargs) -> None:
        """
        Initialize the tracing core with the given configuration.

        Args:
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
            max_queue_size = kwargs.get("max_queue_size", 512)
            max_wait_time = kwargs.get("max_wait_time", 5000)

            # Create a TracingConfig from kwargs with proper defaults
            config: TracingConfig = {
                "service_name": kwargs.get("service_name", "agentops"),
                "exporter": kwargs.get("exporter"),
                "processor": kwargs.get("processor"),
                "exporter_endpoint": kwargs.get("exporter_endpoint", "https://otlp.agentops.ai/v1/traces"),
                "metrics_endpoint": kwargs.get("metrics_endpoint", "https://otlp.agentops.ai/v1/metrics"),
                "max_queue_size": max_queue_size,
                "max_wait_time": max_wait_time,
                "api_key": kwargs.get("api_key"),
                "project_id": kwargs.get("project_id"),
            }

            self._config = config

            # Span types are registered in the constructor
            # No need to register them here anymore

            # Create provider with safe access to service_name
            service_name = config.get("service_name") or "agentops"

            # Create resource attributes dictionary
            resource_attrs = {ResourceAttributes.SERVICE_NAME: service_name}

            # Add project_id to resource attributes if available
            project_id = config.get("project_id")
            if project_id:
                # Add project_id as a custom resource attribute
                resource_attrs[ResourceAttributes.PROJECT_ID] = project_id
                logger.debug(f"Including project_id in resource attributes: {project_id}")

            resource = Resource(resource_attrs)
            self._provider = TracerProvider(resource=resource)

            # Set as global provider
            trace.set_tracer_provider(self._provider)

            # Use default authenticated processor and exporter if api_key is available
            exporter = OTLPSpanExporter(
                endpoint=config.get("exporter_endpoint"), headers={"Authorization": f"Bearer {kwargs.get('jwt')}"}
            )
            # Regular processor for normal spans and immediate export
            processor = BatchSpanProcessor(
                exporter,
                max_export_batch_size=config.get("max_queue_size", max_queue_size),
                schedule_delay_millis=config.get("max_wait_time", max_wait_time),
            )
            self._provider.add_span_processor(processor)
            self._provider.add_span_processor(
                InternalSpanProcessor()
            )  # Catches spans for AgentOps on-terminal printing
            self._processors.append(processor)

            metric_reader = PeriodicExportingMetricReader(
                OTLPMetricExporter(
                    endpoint=config.get("metrics_endpoint"), headers={"Authorization": f"Bearer {kwargs.get('jwt')}"}
                )
            )
            meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
            metrics.set_meter_provider(meter_provider)
            self._initialized = True
            logger.debug("Tracing core initialized")

    @property
    def initialized(self) -> bool:
        """Check if the tracing core is initialized."""
        return self._initialized

    def shutdown(self) -> None:
        """Shutdown the tracing core."""
        if not self._initialized:
            return

        with self._lock:
            if not self._initialized:
                return

            # Flush processors
            for processor in self._processors:
                try:
                    processor.force_flush()
                except Exception as e:
                    logger.warning(f"Error flushing processor: {e}")

            # Shutdown provider
            if self._provider:
                try:
                    self._provider.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down provider: {e}")

            self._initialized = False
            logger.debug("Tracing core shutdown")

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
