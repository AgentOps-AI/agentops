"""Tests for OpenTelemetry instrumentation in Session and Events"""

from uuid import uuid4

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from agentops.config import Configuration
from agentops.event import ActionEvent, EventType
from agentops.session.session import EndState, Session


def setup_test_tracer():
    """Set up a test tracer with console exporter"""
    provider = TracerProvider()
    processor = SimpleSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)


def test_session_event_span_hierarchy():
    """Test that Event spans are children of their Session span"""
    setup_test_tracer()

    # Create a session with proper UUID
    session = Session(session_id=uuid4(), config=Configuration())
    session_span_id = session.span.get_span_context().span_id

    # Record an event - should create child span
    event = ActionEvent(event_type=EventType.ACTION)  # Specify required field
    session.record(event)
    event_span_id = event.span.get_span_context().span_id
    event_parent_id = event.span.get_span_context().parent_id

    # Verify parent-child relationship
    assert event_parent_id == session_span_id, (
        f"Event span parent ID {event_parent_id} should match "
        f"session span ID {session_span_id}"
    )

    # End session
    session.end(EndState.SUCCESS.value)