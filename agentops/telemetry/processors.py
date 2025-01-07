import json
import time
from datetime import datetime, timezone
from threading import Event, Lock, Thread
from typing import Any, Dict, Optional, List
from uuid import UUID, uuid4

from opentelemetry import trace
from opentelemetry.context import Context, attach, detach, set_value
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.trace import Span as OTELSpan

from agentops.helpers import filter_unjsonable, get_ISO_time
from agentops.telemetry.converter import EventToSpanConverter


class EventProcessor:
    """
    Handles event processing and formatting for AgentOps telemetry.
    
    This class follows the OpenTelemetry pattern where:
    1. A TracerProvider manages span processors and creates tracers
    2. Tracers create spans
    3. Spans are automatically processed by all processors registered with the provider
    
    This design ensures:
    - Loose coupling: Processors don't need to know about each other
    - Flexibility: Processors can be added/removed via the provider
    - Standard compliance: Follows OpenTelemetry's recommended architecture
    """

    def __init__(self, session_id: UUID, tracer_provider: Optional[TracerProvider] = None):
        """
        Initialize the event processor with a session ID and optional tracer provider.
        
        Args:
            session_id: Unique identifier for the telemetry session
            tracer_provider: Optional TracerProvider. If not provided, creates a new one.
                           In production, you typically want to pass in a configured provider
                           with the desired span processors already registered.
        """
        self.session_id = session_id
        # Use provided provider or create new one. In production, you should pass in
        # a configured provider to ensure consistent span processing across the application
        self._tracer_provider = tracer_provider or TracerProvider()
        self._tracer = self._tracer_provider.get_tracer(__name__)
        self.event_counts: Dict[str, int] = {
            "llms": 0,
            "tools": 0,
            "actions": 0,
            "errors": 0,
            "apis": 0,
        }

    def process_event(self, event: Any, tags: Optional[List[str]] = None, flush_now: bool = False) -> Optional[Span]:
        """
        Process and format an event into OpenTelemetry spans using EventToSpanConverter.
        
        Args:
            event: The event to process
            tags: Optional list of tags to attach to the span
            flush_now: Whether to force flush the span immediately
        
        Returns:
            The primary span created for the event
        """
        # Ensure required attributes
        if not hasattr(event, "id"):
            event.id = uuid4()
        if not hasattr(event, "init_timestamp"):
            event.init_timestamp = get_ISO_time()
        if not hasattr(event, "end_timestamp") or event.end_timestamp is None:
            event.end_timestamp = get_ISO_time()

        # For error events, use the current span if it exists
        if hasattr(event, "error_type"):
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                current_span.set_attribute("error", True)
                current_span.set_attribute("error.type", event.error_type)
                current_span.set_attribute("error.details", event.details)
                if hasattr(event, "trigger_event") and event.trigger_event:
                    current_span.set_attribute("trigger_event.id", str(event.trigger_event.id))
                    current_span.set_attribute("trigger_event.type", event.trigger_event.event_type)
                return current_span

        # Create session context
        token = set_value("session.id", str(self.session_id))
        try:
            token = attach(token)
            
            # Get span definitions from converter
            span_definitions = EventToSpanConverter.convert_event(event)
            primary_span = None
            
            # Create spans based on definitions
            for span_def in span_definitions:
                context = None
                if span_def.parent_span_id and primary_span:
                    context = trace.set_span_in_context(primary_span)
                    
                # Add common attributes
                span_def.attributes.update({
                    "event.id": str(event.id),
                    "session.id": str(self.session_id),
                    "session.tags": ",".join(tags) if tags else "",
                    "event.timestamp": event.init_timestamp,
                    "event.end_timestamp": event.end_timestamp,
                })
                
                with self._tracer.start_span(
                    name=span_def.name,
                    kind=span_def.kind,
                    attributes=span_def.attributes,
                    context=context,
                ) as span:
                    if not primary_span:
                        primary_span = span
                        # Update event counts for primary span
                        if event.event_type in self.event_counts:
                            self.event_counts[event.event_type] += 1
                    
                    if flush_now:
                        span.end()
                        
            return primary_span

        finally:
            detach(token)

    def _format_event_data(self, event: Any) -> Dict[str, Any]:
        """Format event data based on event type"""
        event_data = dict(filter_unjsonable(event.__dict__))

        if hasattr(event, "error_type"):
            event_data["error_type"] = getattr(event, "error_type", event.event_type)
        elif event.event_type == "actions":
            if "action_type" not in event_data:
                event_data["action_type"] = event_data.get("name", "unknown_action")
            if "name" not in event_data:
                event_data["name"] = event_data.get("action_type", "unknown_action")
        elif event.event_type == "tools":
            if "name" not in event_data:
                event_data["name"] = event_data.get("tool_name", "unknown_tool")
            if "tool_name" not in event_data:
                event_data["tool_name"] = event_data.get("name", "unknown_tool")

        return event_data


class LiveSpanProcessor(SpanProcessor):
    """
    This processor is particularly useful for monitoring long-running operations
    where you want to see progress before completion, rather than only getting
    visibility after the fact.

    Integrates with the broader OpenTelemetry system through the
    standard SpanProcessor interface, but adds the specialized capability of exporting
    intermediate states of spans, which is not typically available in standard OTEL processors.
    """

    def __init__(self, span_exporter: SpanExporter):
        self.span_exporter = span_exporter
        self._in_flight: Dict[int, Span] = {}
        self._lock = Lock()
        self._stop_event = Event()
        self._export_thread = Thread(target=self._export_periodically, daemon=True)
        self._export_thread.start()

    def _export_periodically(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(1)  # Export every second
            with self._lock:
                to_export = [self._readable_span(span) for span in self._in_flight.values()]
                if to_export:
                    self.span_exporter.export(to_export)

    def _readable_span(self, span: OTELSpan) -> ReadableSpan:
        """Convert an OTEL span to a readable span with additional attributes"""
        if not hasattr(span, 'get_span_context'):
            raise ValueError("Invalid span type")
            
        context = span.get_span_context()
        
        # Combine existing attributes with in-flight attributes
        attributes = dict(span.attributes or {})
        attributes.update({
            "agentops.in_flight": True,
            "agentops.event_type": span.attributes.get("event.type", "unknown"),
            "agentops.duration_ms": (time.time_ns() - span.start_time) / 1e6,
        })
        
        # Create new ReadableSpan with all attributes
        readable = ReadableSpan(
            name=span.name,
            context=context,
            parent=None,  # Parent context handled separately
            resource=span.resource,
            attributes=attributes,  # Use combined attributes
            events=span.events,
            links=span.links,
            kind=span.kind,
            status=span.status,
            start_time=span.start_time,
            end_time=time.time_ns(),
            instrumentation_scope=span.instrumentation_scope,
        )
        
        return readable

    def on_start(self, span: OTELSpan, parent_context: Optional[Context] = None) -> None:
        """Handle span start event"""
        context = span.get_span_context()
        if not context or not context.trace_flags.sampled:
            return
            
        with self._lock:
            self._in_flight[context.span_id] = span
            # Export immediately when span starts
            readable = self._readable_span(span)
            self.span_exporter.export([readable])

    def on_end(self, span: ReadableSpan) -> None:
        """Handle span end event"""
        if not span.context or not span.context.trace_flags.sampled:
            return
        with self._lock:
            # Remove from in-flight and export final state
            if span.context.span_id in self._in_flight:
                del self._in_flight[span.context.span_id]
            self.span_exporter.export((span,))

    def shutdown(self) -> None:
        self._stop_event.set()
        self._export_thread.join()
        self.span_exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
