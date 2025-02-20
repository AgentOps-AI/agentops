"""Tests for session tracing functionality."""

from uuid import uuid4

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.trace import SpanKind

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
    # Initialize tracer
    setup_session_tracer(agentops_session)

    # Verify tracer was initialized
    assert hasattr(agentops_session, "_tracer"), "Session tracer not initialized"
    assert isinstance(agentops_session._tracer, SessionTracer), "Wrong tracer type"

    # Test basic tracing operations
    with agentops_session._tracer.start_root_span() as root_span:
        # Now we can start operations
        with agentops_session._tracer.start_operation("test_operation") as span:
            span.set_attribute("test.attribute", "test_value")

            # Nested operation
            with agentops_session._tracer.start_operation("nested_operation") as nested_span:
                nested_span.set_attribute("nested.attribute", "nested_value")

    # Verify tracer was registered
    assert str(agentops_session.session_id) in _session_tracers, "Tracer not registered"


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

    # Verify both sessions have tracers
    assert hasattr(session1, "_tracer")
    assert hasattr(session2, "_tracer")

    # Verify tracers are different
    assert session1.tracer != session2.tracer

    # Test operations don't interfere
    with session1.tracer.start_root_span() as root1:
        with session2.tracer.start_root_span() as root2:
            with session1.tracer.start_operation("op1") as span1:
                with session2.tracer.start_operation("op2") as span2:
                    span1.set_attribute("session", "1")
                    span2.set_attribute("session", "2")

    # Clean up
    cleanup_session_tracer(session1)
    cleanup_session_tracer(session2)


@pytest.mark.asyncio
async def test_async_session_tracing(agentops_session):
    """Test session tracing in async context"""
    setup_session_tracer(agentops_session)

    async def traced_operation():
        with agentops_session.tracer.start_root_span() as root:
            with agentops_session.tracer.start_operation("async_op") as span:
                span.set_attribute("async", True)
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
