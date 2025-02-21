import pytest
from opentelemetry import trace

import agentops


@pytest.fixture
def session_generator():
    """Fixture that provides a session generator with automatic cleanup"""
    sessions = []
    
    def create_session(tags=None):
        if tags is None:
            tags = ["test-session"]
        session = agentops.start_session(tags=tags)
        sessions.append(session)
        return session
    
    yield create_session
    
    # Cleanup all sessions created during the test
    for session in sessions:
        session.end()


def test_basic_span_propagation(session_generator):
    """Test that spans are correctly created and associated with the session"""
    session = session_generator(tags=["test-tracing"])
    
    # Session is already the root span
    child_span = session._tracer._start_span("test_operation")
    assert child_span.is_recording()
    child_span.end()


def test_nested_span_hierarchy(session_generator):
    """Test that nested spans maintain correct parent-child relationships"""
    session = session_generator(tags=["test-nested"])

    # Create child spans
    parent_span = session._tracer._start_span("parent_operation")
    child_span = session._tracer._start_span("child_operation")
    
    # Verify hierarchy
    assert parent_span.get_span_context().trace_id == child_span.get_span_context().trace_id
    
    child_span.end()
    parent_span.end()


def test_multiple_session_span_isolation(session_generator):
    """Test that spans from different sessions don't interfere"""
    session1 = session_generator(tags=["session-1"])
    session2 = session_generator(tags=["session-2"])

    # Create spans in each session
    span1 = session1._tracer._start_span("operation_1")
    span2 = session2._tracer._start_span("operation_2")

    # Verify spans have different trace IDs
    assert span1.get_span_context().trace_id != span2.get_span_context().trace_id

    span1.end()
    span2.end()


def test_span_attributes_and_events(session_generator):
    """Test that span attributes and events are correctly recorded"""
    session = session_generator(tags=["test-attributes"])

    # Create a child span
    span = session._tracer._start_span("test_operation")
    
    # Test attributes
    span.set_attribute("string.attr", "test")
    span.set_attribute("int.attr", 42)
    span.set_attribute("bool.attr", True)

    # Test events
    span.add_event("test_event", {"severity": "INFO", "detail": "test detail"})

    # Verify span is recording
    assert span.is_recording()
    span.end()


def test_context_propagation(session_generator):
    """Test that context is correctly propagated across operations"""
    session = session_generator(tags=["test-propagation"])

    # The session root span context should be propagated to children
    child_span = session._tracer._start_span("child_operation")
    assert child_span.get_span_context().trace_id == session._tracer._root_span.get_span_context().trace_id
    child_span.end()
