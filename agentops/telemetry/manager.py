"""Telemetry manager for OpenTelemetry integration."""

from typing import Dict, Any, Optional
from datetime import datetime, timezone

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace import Status, StatusCode, SpanKind, NonRecordingSpan, INVALID_SPAN_CONTEXT

class TelemetryManager:
    """Manages OpenTelemetry integration for AgentOps.
    
    This class handles the setup and management of OpenTelemetry tracing,
    including span creation, context propagation, and attribute management.
    """
    
    def __init__(
        self,
        service_name: str,
        otlp_endpoint: str,
        enabled: bool = True,
        postgres_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the telemetry manager.
        
        Args:
            service_name: Name of the service for telemetry.
            otlp_endpoint: Endpoint for the OTLP exporter.
            enabled: Whether telemetry is enabled.
            postgres_config: Optional configuration for PostgreSQL exporter.
        """
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint
        self.enabled = enabled
        
        if not enabled:
            return
            
        # Create and configure the tracer provider
        resource = Resource.create({
            SERVICE_NAME: service_name,
            "agentops.version": "1.0",  # TODO: Get from package version
        })
        tracer_provider = TracerProvider(resource=resource)
        
        # Set up the OTLP exporter for Jaeger
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        otlp_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(otlp_processor)
        
        # Set up PostgreSQL exporter if configured
        if postgres_config:
            from .postgres_exporter import PostgresSpanExporter
            postgres_exporter = PostgresSpanExporter(**postgres_config)
            postgres_processor = BatchSpanProcessor(postgres_exporter)
            tracer_provider.add_span_processor(postgres_processor)
        
        # Set the tracer provider
        trace.set_tracer_provider(tracer_provider)
        self.tracer = trace.get_tracer(__name__)
        
    def create_session_span(
        self,
        session_id: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> trace.Span:
        """Create a root span for a session.
        
        Args:
            session_id: The ID of the session.
            attributes: Optional additional attributes for the span.
            
        Returns:
            The created session span.
        """
        if not self.enabled:
            return NonRecordingSpan(INVALID_SPAN_CONTEXT)
            
        base_attributes = {
            "session.id": session_id,
            "service.name": self.service_name,
        }
        if attributes:
            base_attributes.update(attributes)
            
        return self.tracer.start_span(
            name="session",
            kind=SpanKind.SERVER,
            attributes=base_attributes
        )
        
    def create_agent_span(
        self,
        agent_id: str,
        session_context: Optional[trace.Context] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> trace.Span:
        """Create a span for an agent.
        
        Args:
            agent_id: The ID of the agent.
            session_context: The context from the session span.
            attributes: Optional additional attributes.
            
        Returns:
            The created agent span.
        """
        if not self.enabled:
            return NonRecordingSpan(INVALID_SPAN_CONTEXT)
            
        base_attributes = {
            "agent.id": agent_id,
            "service.name": self.service_name,
        }
        if attributes:
            base_attributes.update(attributes)
            
        return self.tracer.start_span(
            name="agent",
            context=session_context,
            kind=SpanKind.INTERNAL,
            attributes=base_attributes
        )
        
    def create_event_span(
        self,
        event_type: str,
        event_id: str,
        agent_context: Optional[trace.Context] = None,
        attributes: Optional[Dict[str, Any]] = None,
        kind: SpanKind = SpanKind.INTERNAL
    ) -> trace.Span:
        """Create a span for an event.
        
        Args:
            event_type: The type of event.
            event_id: The ID of the event.
            agent_context: The context from the agent span.
            attributes: Additional attributes for the span.
            kind: Kind of span (default: INTERNAL)
            
        Returns:
            The created event span.
        """
        if not self.enabled:
            return NonRecordingSpan(INVALID_SPAN_CONTEXT)
            
        base_attributes = {
            "event.type": event_type,
            "event.id": event_id,
            "service.name": self.service_name,
        }
        if attributes:
            base_attributes.update(attributes)
            
        return self.tracer.start_span(
            name=f"event.{event_type}",
            context=agent_context,
            kind=kind,
            attributes=base_attributes
        )
