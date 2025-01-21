from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, Sampler, TraceIdRatioBased

from .config import OTELConfig
from .processors import EventProcessor

if TYPE_CHECKING:
    from opentelemetry.sdk._logs import LoggingHandler

    from agentops.client import Client


class TelemetryManager:
    """Manages OpenTelemetry instrumentation for AgentOps.

    Responsibilities:
    1. Configure and manage TracerProvider
    2. Handle resource attributes and sampling
    3. Manage exporters and processors
    4. Coordinate telemetry lifecycle
    5. Handle logging setup and configuration

    Architecture:
        TelemetryManager
            |
            |-- TracerProvider (configured with sampling)
            |-- Resource (service info and attributes)
            |-- SpanExporters
            |-- EventProcessors
            |-- LoggingHandler (OTLP logging)
    """

    def __init__(self, client: Optional[Client] = None) -> None:
        self._provider: Optional[TracerProvider] = None
        self._exporters: Dict[UUID, SpanExporter] = {}
        self._processors: List[SpanProcessor] = []
        self._log_handler: Optional[LoggingHandler] = None
        self.config: Optional[OTELConfig] = None

        if not client:
            from agentops.client import Client

            client = Client()
        self.client = client

    def set_log_handler(self, log_handler: Optional[LoggingHandler]) -> None:
        """Set the OTLP log handler.

        Args:
            log_handler: The logging handler to use for OTLP
        """
        self._log_handler = log_handler

    def get_log_handler(self) -> Optional[LoggingHandler]:
        """Get the current OTLP log handler.

        Returns:
            The current logging handler if set, None otherwise
        """
        return self._log_handler

    def add_telemetry_log_handler(self, logger: logging.Logger) -> None:
        """Add the OTLP log handler to the given logger if configured.

        Args:
            logger: The logger to add the handler to
        """
        if self._log_handler:
            logger.addHandler(self._log_handler)

    def initialize(self, config: OTELConfig) -> None:
        """Initialize telemetry infrastructure.

        Args:
            config: OTEL configuration

        Raises:
            ValueError: If config is None
        """
        if not config:
            raise ValueError("Config is required")

        self.config = config

        # Create resource with service info
        resource = Resource.create({"service.name": "agentops", **(config.resource_attributes or {})})

        # Create provider
        self._provider = TracerProvider(resource=resource)

        # Set up logging handler with the same resource
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter

        # Set as global provider
        trace.set_tracer_provider(self._provider)

    def create_tracer(self, entity_id: UUID, exporter: SpanExporter) -> trace.Tracer:
        """Create tracer with a specific exporter.

        Args:
            entity_id: UUID for the entity being traced
            exporter: SpanExporter implementation to use

        Returns:
            Configured tracer

        Raises:
            RuntimeError: If telemetry is not initialized
        """
        if not self._provider:
            raise RuntimeError("Telemetry not initialized")
        if not self.config:
            raise RuntimeError("Config not initialized")

        # Create processors
        batch_processor = BatchSpanProcessor(
            exporter,
            max_queue_size=self.config.max_queue_size,
            max_export_batch_size=self.config.max_export_batch_size,
            schedule_delay_millis=self.config.max_wait_time,
        )

        # Wrap with event processor
        event_processor = EventProcessor(entity_id=entity_id, processor=batch_processor)

        # Add processors
        self._provider.add_span_processor(event_processor)
        self._processors.append(event_processor)
        self._exporters[entity_id] = exporter

        # Return tracer
        return self._provider.get_tracer(f"agentops.tracer.{entity_id}")

    def cleanup_tracer(self, entity_id: UUID) -> None:
        """Clean up tracer telemetry resources.

        Args:
            entity_id: UUID of entity to clean up
        """
        if entity_id in self._exporters:
            exporter = self._exporters[entity_id]
            exporter.shutdown()
            del self._exporters[entity_id]

    def shutdown(self) -> None:
        """Shutdown all telemetry resources."""
        if self._provider:
            self._provider.shutdown()
            self._provider = None
        for exporter in self._exporters.values():
            exporter.shutdown()
        self._exporters.clear()
        self._processors.clear()
