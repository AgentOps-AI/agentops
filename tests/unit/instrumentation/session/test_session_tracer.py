"""Tests for session tracing functionality."""

from uuid import uuid4

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.trace import SpanKind

import agentops
from agentops import Config, Session
from agentops.instrumentation.session.tracer import (SessionInstrumentor,
                                                     SessionTracer,
                                                     _session_tracers,
                                                     cleanup_session_tracer,
                                                     get_session_tracer,
                                                     setup_session_tracer)


@pytest.fixture(autouse=True)
def reset_instrumentation():
    """Reset instrumentation state between tests"""
    _session_tracers.clear()
    SessionInstrumentor._is_instrumented = False
    yield




def test_session_tracer_initialization(agentops_session):
    """Test that session tracer is properly initialized"""
    setup_session_tracer(agentops_session)

    # Verify tracer was initialized with root span
    assert hasattr(agentops_session, "_tracer")
    assert isinstance(agentops_session._tracer, SessionTracer)
    assert agentops_session._tracer._root_span is not None
    assert agentops_session._tracer._root_span.is_recording()

    # Verify root span has correct attributes
    root_span = agentops_session._tracer._root_span
    assert root_span.attributes["session.id"] == str(agentops_session.session_id)
    assert root_span.attributes["session.type"] == "root"

    # Test internal span creation
    child_span = agentops_session._tracer._start_span("test_operation")
    assert child_span.is_recording()
    child_span.set_attribute("test.attribute", "test_value")
    child_span.end()


def test_session_tracer_cleanup(agentops_session):
    """Test that session tracer is properly cleaned up"""
    # Setup tracer
    setup_session_tracer(agentops_session)
    session_id = str(agentops_session.session_id)

    # Verify tracer exists
    assert session_id in _session_tracers

    # Clean up tracer
    cleanup_session_tracer(agentops_session)

    # Verify tracer was cleaned up
    assert session_id not in _session_tracers, "Tracer not cleaned up"


def test_multiple_session_tracers():
    """Test that multiple sessions can have independent tracers"""
    session1 = Session(session_id=uuid4(), config=Config(api_key="test-key"))
    session2 = Session(session_id=uuid4(), config=Config(api_key="test-key"))

    setup_session_tracer(session1)
    setup_session_tracer(session2)

    # Verify both sessions have tracers and root spans
    assert hasattr(session1, "_tracer")
    assert hasattr(session2, "_tracer")
    assert session1._tracer._root_span is not None
    assert session2._tracer._root_span is not None

    # Verify tracers are different
    assert session1.tracer != session2.tracer
    assert session1._tracer._root_span != session2._tracer._root_span

    # Clean up
    cleanup_session_tracer(session1)
    cleanup_session_tracer(session2)


@pytest.mark.asyncio
async def test_async_session_tracing(agentops_session):
    """Test session tracing in async context"""
    setup_session_tracer(agentops_session)

    async def traced_operation():
        # The session is already the root span
        child_span = agentops_session._tracer._start_span("async_op")
        child_span.set_attribute("async", True)
        child_span.end()
        return "success"

    result = await traced_operation()
    assert result == "success"


def test_get_session_tracer(agentops_session):
    """Test retrieving tracer by session ID."""
    # Setup tracer
    setup_session_tracer(agentops_session)
    session_id = str(agentops_session.session_id)

    # Test retrieval
    tracer = get_session_tracer(session_id)
    assert tracer is not None
    assert isinstance(tracer, SessionTracer)

    # Test non-existent session
    assert get_session_tracer("non-existent") is None


def test_weak_reference_cleanup(agentops_session):
    """Test that tracers are properly garbage collected."""
    setup_session_tracer(agentops_session)
    session_id = str(agentops_session.session_id)
    
    # Get the instrumentor
    instrumentor = _session_tracers[session_id]
    
    # Store weak reference count
    initial_count = len(_session_tracers)
    
    # Clean up the session properly
    cleanup_session_tracer(agentops_session)
    del agentops_session
    
    # Force garbage collection
    import gc
    gc.collect()
    
    # Check that tracer was removed
    assert len(_session_tracers) == 0, "Tracer not properly cleaned up"


if __name__ == "__main__":
    pytest.main()
