from typing import TYPE_CHECKING, Dict, Optional, Union
from uuid import UUID
import os

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

from agentops.config import Configuration
from agentops.log_config import logger
from .config import OTELConfig
from .exporter import ExportManager
from .manager import OTELManager
from .processors import LiveSpanProcessor


if TYPE_CHECKING:
    from agentops.session import Session


class ClientTelemetry:
    """Manages telemetry at the agentops.Client level, shared across sessions"""

    def __init__(self):
        self._otel_manager: Optional[OTELManager] = None
        self._tracer_provider: Optional[TracerProvider] = None
        self._session_exporters: Dict[UUID, ExportManager] = {}
        self.config: Optional[OTELConfig] = None

    def initialize(self, config: OTELConfig) -> None:
        """Initialize telemetry components"""
        # Check for environment variables if no exporters configured
        if not config.additional_exporters:
            endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
            service_name = os.environ.get("OTEL_SERVICE_NAME")
            
            if service_name and not config.resource_attributes:
                config.resource_attributes = {"service.name": service_name}
            
            if endpoint:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                config.additional_exporters = [OTLPSpanExporter(endpoint=endpoint)]
                logger.info("Using OTEL configuration from environment variables")
        
        # Validate exporters
        if config.additional_exporters:
            for exporter in config.additional_exporters:
                if not isinstance(exporter, SpanExporter):
                    raise ValueError(f"Invalid exporter type: {type(exporter)}. Must be a SpanExporter")
        
        # Create the OTEL manager instance
        self._otel_manager = OTELManager(
            config=config,
            exporters=config.additional_exporters,
            resource_attributes=config.resource_attributes,
            sampler=config.sampler
        )
        self.config = config

        # Initialize the tracer provider with global service info
        self._tracer_provider = self._otel_manager.initialize(
            service_name="agentops",
            session_id="global"
        )

    def get_session_tracer(self, session_id: UUID, jwt: str):
        """Get or create a tracer for a specific session"""
        # Create session-specific exporter
        exporter = ExportManager(
            session_id=session_id,
            endpoint=self.config.endpoint,
            jwt=jwt,
            api_key=self.config.api_key,
            retry_config=self.config.retry_config if self.config else None,
            custom_formatters=self.config.custom_formatters if self.config else None,
        )

        # Store exporter reference
        self._session_exporters[session_id] = exporter

        # Add both batch and in-flight processors
        batch_processor = BatchSpanProcessor(
            exporter,
            max_queue_size=self.config.max_queue_size,
            schedule_delay_millis=config.max_wait_time,
            max_export_batch_size=min(
                max(self.config.max_queue_size // 20, 1),
                min(self.config.max_queue_size, 32),
            ),
            export_timeout_millis=20000,
        )

        # Add in-flight processor for long-running operations
        inflight_processor = LiveSpanProcessor(exporter)

        self._otel_manager.add_processor(batch_processor)
        self._otel_manager.add_processor(inflight_processor)

        # Return session-specific tracer
        return self._tracer_provider.get_tracer(f"agentops.session.{str(session_id)}")

    def cleanup_session(self, session_id: UUID):
        """Clean up telemetry resources for a session"""
        if session_id in self._session_exporters:
            exporter = self._session_exporters[session_id]
            exporter.shutdown()
            del self._session_exporters[session_id]

    def shutdown(self):
        """Shutdown all telemetry"""
        if self._otel_manager:
            self._otel_manager.shutdown()
        for exporter in self._session_exporters.values():
            exporter.shutdown()
        self._session_exporters.clear()

    def force_flush(self) -> bool:
        """Force flush all processors"""
        if not self._otel_manager:
            return True
        
        success = True
        for processor in self._otel_manager._processors:
            try:
                if not processor.force_flush():
                    success = False
            except Exception as e:
                logger.error(f"Error flushing processor: {e}")
                success = False
        
        return success
