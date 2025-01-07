from typing import Dict, Optional
from uuid import UUID

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .config import OTELConfig
from .exporter import ExportManager
from .manager import OTELManager
from .processors import LiveSpanProcessor


class ClientTelemetry:
    """Manages telemetry at the agentops.Client level, shared across sessions"""

    def __init__(self):
        self._otel_manager: Optional[OTELManager] = None
        self._tracer_provider: Optional[TracerProvider] = None
        self._session_exporters: Dict[UUID, ExportManager] = {}
        self._otel_config: Optional[OTELConfig] = None

    def initialize(self, config, otel_config: Optional[OTELConfig] = None):
        """Initialize telemetry with configuration"""
        self._otel_config = otel_config
        self._otel_manager = OTELManager(config)

        if otel_config:
            self._otel_manager.configure(
                additional_exporters=otel_config.additional_exporters,
                resource_attributes=otel_config.resource_attributes,
                sampler=otel_config.sampler,
            )

        # Initialize shared tracer provider
        self._tracer_provider = self._otel_manager.initialize(service_name="agentops.client", session_id="global")

    def get_session_tracer(self, session_id: UUID, config, jwt: str):
        """Get or create a tracer for a specific session"""
        # Create session-specific exporter
        exporter = ExportManager(
            session_id=session_id,
            endpoint=config.endpoint,
            jwt=jwt,
            api_key=config.api_key,
            retry_config=self._otel_config.retry_config if self._otel_config else None,
            custom_formatters=self._otel_config.custom_formatters if self._otel_config else None,
        )

        # Store exporter reference
        self._session_exporters[session_id] = exporter

        # Add both batch and in-flight processors
        batch_processor = BatchSpanProcessor(
            exporter,
            max_queue_size=config.max_queue_size,
            schedule_delay_millis=config.max_wait_time,
            max_export_batch_size=min(
                max(config.max_queue_size // 20, 1),
                min(config.max_queue_size, 32),
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