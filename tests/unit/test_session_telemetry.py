"""Tests for OpenTelemetry instrumentation in Session and Events"""

from uuid import uuid4

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from agentops.config import Configuration
from agentops.event import ActionEvent, EventType
from agentops.session.session import EndState, Session


@pytest.fixture(autouse=True)
def setup_test_tracer():
    """Set up a test tracer with console exporter"""
    provider = TracerProvider()
    processor = SimpleSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    yield
    # Reset the tracer provider after test
    trace.set_tracer_provider(None)


def test_session_event_span_hierarchy(setup_test_tracer):
    """Test that Event spans are children of their Session span"""
    # Create a session with proper UUID
    session = Session(session_id=uuid4(), config=Configuration())
    assert session.span is not None, "Session span should be created in __post_init__"
    session_span_id = session.span.get_span_context().span_id

    # Record an event - should create child span
    event = ActionEvent(event_type=EventType.ACTION)
    session.record(event)
    assert event.span is not None, "Event span should be created during session.record()"
    
    # Get parent span ID from context
    context = event.span.get_span_context()
    assert context.trace_id == session.span.get_span_context().trace_id, (
        "Event should be in same trace as Session"
    )
    
    # Print debug info
    print(f"Session span ID: {session_span_id}")
    print(f"Event context: {context}")
    print(f"Event parent: {event.span.parent}")


def test_instrumented_base_creates_span(setup_test_tracer):
    """Test that any InstrumentedBase object gets a span on creation"""
    # Test with both Session and Event
    session = Session(session_id=uuid4(), config=Configuration())
    assert session.span is not None, "Session should have a span"
    
    event = ActionEvent(event_type=EventType.ACTION)
    assert event.span is not None, "Event should have a span"
    
    # Verify spans have proper context
    assert session.span.get_span_context().is_valid
    assert event.span.get_span_context().is_valid


def test_event_span_survives_recording(setup_test_tracer):
    """Test that event's span remains after being recorded"""
    session = Session(session_id=uuid4(), config=Configuration())
    event = ActionEvent(event_type=EventType.ACTION)
    
    # Verify span exists before recording
    assert event.span is not None, "Event should have span before recording"
    before_span_id = event.span.get_span_context().span_id
    
    # Record event
    session.record(event)
    
    # Verify span still exists and is the same
    assert event.span is not None, "Event should still have span after recording"
    after_span_id = event.span.get_span_context().span_id
    assert before_span_id == after_span_id, "Event span should not change during recording"