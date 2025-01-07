from typing import Dict, List, Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource, ResourceAttributes
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, Sampler, TraceIdRatioBased

from agentops.config import Configuration
from agentops.telemetry.config import OTELConfig


class OTELManager:
    """
    Manages OpenTelemetry setup and configuration for AgentOps.
    
    This manager follows OpenTelemetry best practices:
    1. Configuration is done at initialization
    2. TracerProvider is configured once with all necessary processors
    3. Resource attributes and sampling are set at provider creation
    4. Each processor handles one exporter
    
    The manager supports any SpanProcessor implementation that follows
    the OpenTelemetry processor interface, including:
    - BatchSpanProcessor: For efficient batched exports
    - SimpleSpanProcessor: For immediate exports
    - LiveSpanProcessor: For real-time monitoring
    - EventProcessor: For event-specific processing
    - Custom processors: Any class implementing SpanProcessor interface
    """

    def __init__(
        self,
        config: OTELConfig,
        exporters: Optional[List[SpanExporter]] = None,
        resource_attributes: Optional[Dict] = None,
        sampler: Optional[Sampler] = None,
    ):
        """
        Initialize the manager with all necessary configuration.
        
        Args:
            config: Base configuration for processors
            exporters: List of exporters to use (each gets its own processor)
            resource_attributes: Custom resource attributes
            sampler: Custom sampling strategy
        """
        self.config = config
        self._tracer_provider = None
        self._processors: List[SpanProcessor] = []
        self._resource_attributes = resource_attributes or {}
        self._sampler = sampler
        self._exporters = exporters or []

    def initialize(self, service_name: str, session_id: str) -> TracerProvider:
        """
        Initialize OTEL components with proper resource attributes.
        Creates the TracerProvider and configures all processors.
        
        Args:
            service_name: Name of the service
            session_id: Unique session identifier
            
        Returns:
            Configured TracerProvider instance
        """
        # Set up resource attributes
        resource_attributes = {
            ResourceAttributes.SERVICE_NAME: service_name,
            "session.id": session_id,
        }
        resource_attributes.update(self._resource_attributes)
        
        # Create resource with attributes
        resource = Resource.create(attributes=resource_attributes)

        # Create provider with resource and sampling config
        self._tracer_provider = TracerProvider(
            resource=resource,
            sampler=self._sampler or ParentBased(TraceIdRatioBased(1.0)),
        )

        # Set up processors for all configured exporters
        for exporter in self._exporters:
            processor = BatchSpanProcessor(
                exporter,
                max_queue_size=self.config.max_queue_size,
                schedule_delay_millis=self.config.max_wait_time,
            )
            self._tracer_provider.add_span_processor(processor)
            self._processors.append(processor)

        # Set as global tracer provider
        trace.set_tracer_provider(self._tracer_provider)

        return self._tracer_provider

    def add_processor(self, processor: SpanProcessor):
        """
        Add a custom span processor to the tracer provider.
        
        Args:
            processor: Any span processor implementation
        
        Raises:
            RuntimeError: If manager is not initialized
        """
        if not self._tracer_provider:
            raise RuntimeError("OTELManager not initialized")
            
        self._tracer_provider.add_span_processor(processor)
        self._processors.append(processor)

    def get_tracer(self, name: str) -> trace.Tracer:
        """
        Get a tracer instance for the given name.
        
        Args:
            name: Name for the tracer, typically __name__
            
        Returns:
            Configured tracer instance
            
        Raises:
            RuntimeError: If manager is not initialized
        """
        if not self._tracer_provider:
            raise RuntimeError("OTELManager not initialized")
        return self._tracer_provider.get_tracer(name)

    def shutdown(self):
        """
        Shutdown all processors and cleanup resources.
        Ensures proper cleanup of all processor types.
        """
        for processor in self._processors:
            try:
                if hasattr(processor, 'force_flush'):
                    processor.force_flush(timeout_millis=5000)
                processor.shutdown()
            except Exception:
                pass  # Ensure we continue cleanup even if one processor fails
        self._processors = []
        self._tracer_provider = None

    def configure(
        self,
        additional_exporters: Optional[List[SpanExporter]] = None,
        resource_attributes: Optional[Dict] = None,
        sampler: Optional[Sampler] = None,
    ) -> None:
        """
        Configure the OTEL manager with additional settings.
        
        Args:
            additional_exporters: Additional span exporters to use
            resource_attributes: Custom resource attributes to add
            sampler: Custom sampling strategy
        """
        if additional_exporters:
            self._exporters.extend(additional_exporters)
        if resource_attributes:
            self._resource_attributes.update(resource_attributes)
        if sampler:
            self._sampler = sampler
