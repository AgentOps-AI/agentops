from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, Sampler, TraceIdRatioBased

from .config import OTELConfig
from .exporters.session import SessionExporter
from .processors import EventProcessor



if TYPE_CHECKING:
    from agentops.client import Client


class TelemetryManager:
    """Manages OpenTelemetry instrumentation for AgentOps.
    
    Responsibilities:
    1. Configure and manage TracerProvider
    2. Handle resource attributes and sampling
    3. Manage session-specific exporters and processors
    4. Coordinate telemetry lifecycle
    
    Architecture:
        TelemetryManager
            |
            |-- TracerProvider (configured with sampling)
            |-- Resource (service info and attributes)
            |-- SessionExporters (per session)
            |-- EventProcessors (per session)
    """

    def __init__(self, client: Optional[Client] = None) -> None:
        self._provider: Optional[TracerProvider] = None
        self._session_exporters: Dict[UUID, SessionExporter] = {}
        self._processors: List[SpanProcessor] = []
        self.config: Optional[OTELConfig] = None

        if not client:
            from agentops.client import Client
            client = Client()
        self.client = client

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
        resource = Resource.create({
            "service.name": "agentops",
            **(config.resource_attributes or {})
        })
        
        # Create provider with sampling
        sampler = config.sampler or ParentBased(TraceIdRatioBased(0.5))
        self._provider = TracerProvider(
            resource=resource,
            sampler=sampler
        )
        
        # Set as global provider
        trace.set_tracer_provider(self._provider)

    def create_session_tracer(self, session_id: UUID, jwt: str) -> trace.Tracer:
        """Create tracer for a new session.
        
        Args:
            session_id: UUID for the session
            jwt: JWT token for authentication
            
        Returns:
            Configured tracer for the session
            
        Raises:
            RuntimeError: If telemetry is not initialized
        """
        if not self._provider:
            raise RuntimeError("Telemetry not initialized")
        if not self.config:
            raise RuntimeError("Config not initialized")

        # Create session exporter and processor
        exporter = SessionExporter(
            session_id=session_id,
            endpoint=self.config.endpoint,
            jwt=jwt,
            api_key=self.config.api_key
        )
        self._session_exporters[session_id] = exporter

        # Create processors
        batch_processor = BatchSpanProcessor(
            exporter,
            max_queue_size=self.config.max_queue_size,
            schedule_delay_millis=self.config.max_wait_time
        )

        event_processor = EventProcessor(
            session_id=session_id,
            processor=batch_processor
        )

        # Add processor
        self._provider.add_span_processor(event_processor)
        self._processors.append(event_processor)

        # Return session tracer
        return self._provider.get_tracer(f"agentops.session.{session_id}")

    def cleanup_session(self, session_id: UUID) -> None:
        """Clean up session telemetry resources.
        
        Args:
            session_id: UUID of session to clean up
        """
        if session_id in self._session_exporters:
            exporter = self._session_exporters[session_id]
            exporter.shutdown()
            del self._session_exporters[session_id]

    def shutdown(self) -> None:
        """Shutdown all telemetry resources."""
        if self._provider:
            self._provider.shutdown()
            self._provider = None
        for exporter in self._session_exporters.values():
            exporter.shutdown()
        self._session_exporters.clear()
        self._processors.clear()
