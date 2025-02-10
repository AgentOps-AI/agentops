"""
Core OpenTelemetry integration for AgentOps.
"""
from typing import Optional, Dict, Any
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.context import Context, attach, detach

logger = logging.getLogger(__name__)

class TelemetryManager:
    """
    Manages OpenTelemetry integration for AgentOps.
    
    This class handles the setup and configuration of OpenTelemetry tracing,
    including the OTLP exporter setup and span creation/management.
    
    The manager ensures proper service name identification and context propagation
    for session-based tracing.
    """
    
    def __init__(
        self,
        service_name: str = "agentops",
        otlp_endpoint: str = "http://localhost:4318/v1/traces",
        enabled: bool = True
    ):
        """
        Initialize the TelemetryManager.
        
        Args:
            service_name: Name of the service
            otlp_endpoint: OTLP endpoint URL for exporting traces
            enabled: Whether telemetry is enabled
        """
        self.enabled = enabled
        if not enabled:
            logger.info("Telemetry is disabled")
            return
            
        # Create resource with proper service name
        self.resource = Resource.create({
            SERVICE_NAME: service_name,
            "agentops.version": "1.0",  # TODO: Get from package version
        })
            
        # Set up the TracerProvider with resource
        provider = TracerProvider(resource=self.resource)
        
        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
        )
        
        # Add BatchSpanProcessor with OTLP exporter
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        
        # Set as global provider
        trace.set_tracer_provider(provider)
        
        self.tracer = trace.get_tracer(service_name)
        self.propagator = TraceContextTextMapPropagator()
        logger.info(f"Initialized telemetry for service {service_name}")
        
    def create_session_root_span(
        self,
        session_id: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> trace.Span:
        """
        Create a root span for a session.
        
        Args:
            session_id: The session ID to use as trace ID
            attributes: Optional additional attributes
            
        Returns:
            The created root span
        """
        if not self.enabled:
            return trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)
            
        base_attributes = {
            "session.id": session_id,
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
        session_context: Optional[Context] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> trace.Span:
        """
        Create a span for an agent within a session.
        
        Args:
            agent_id: The agent's ID
            session_context: Optional session context to link with
            attributes: Optional additional attributes
            
        Returns:
            The created agent span
        """
        if not self.enabled:
            return trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)
            
        base_attributes = {
            "agent.id": agent_id,
        }
        if attributes:
            base_attributes.update(attributes)
            
        context = session_context if session_context else None
        return self.tracer.start_span(
            name=f"agent.{agent_id}",
            context=context,
            kind=SpanKind.INTERNAL,
            attributes=base_attributes
        )
        
    def create_event_span(
        self,
        name: str,
        agent_context: Optional[Context] = None,
        attributes: Optional[Dict[str, Any]] = None,
        kind: SpanKind = SpanKind.INTERNAL
    ) -> trace.Span:
        """
        Create a span for an event within an agent's context.
        
        Args:
            name: Name of the event span
            agent_context: Optional agent context to link with
            attributes: Optional additional attributes
            kind: Kind of span (default: INTERNAL)
            
        Returns:
            The created event span
        """
        if not self.enabled:
            return trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)
            
        context = agent_context if agent_context else None
        return self.tracer.start_span(
            name=name,
            context=context,
            kind=kind,
            attributes=attributes or {}
        ) 