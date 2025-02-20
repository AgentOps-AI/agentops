import pytest
from opentelemetry import trace

import agentops


def test_basic_span_propagation():
    """Test that spans are correctly created and associated with the session"""
    session = agentops.start_session(tags=["test-tracing"])
    assert session is not None
    
    with session.tracer.start_operation("test_operation") as span:
        # Verify span is active and valid
        current_span = trace.get_current_span()
        assert current_span == span
        assert current_span.get_span_context().is_valid
        
        # Verify span attributes
        span.set_attribute("test.attribute", "test_value")
        assert span.get_span_context().is_valid
        assert "test.attribute" in span.attributes

def test_nested_span_hierarchy():
    """Test that nested spans maintain correct parent-child relationships"""
    session = agentops.start_session(tags=["test-nested"])
    assert session is not None
    
    with session.tracer.start_operation("parent_operation") as parent:
        parent_context = parent.get_span_context()
        
        with session.tracer.start_operation("child_operation") as child:
            child_context = child.get_span_context()
            # Verify parent-child relationship
            assert child.parent.span_id == parent_context.span_id
            assert child.parent.trace_id == parent_context.trace_id

def test_multiple_session_span_isolation():
    """Test that spans from different sessions don't interfere"""
    session1 = agentops.start_session(tags=["session-1"])
    session2 = agentops.start_session(tags=["session-2"])
    
    with session1.tracer.start_operation("operation_1") as span1:
        with session2.tracer.start_operation("operation_2") as span2:
            # Verify spans have different trace IDs
            assert span1.get_span_context().trace_id != span2.get_span_context().trace_id
            # Verify current span is from the innermost context
            current_span = trace.get_current_span()
            assert current_span == span2

def test_span_attributes_and_events():
    """Test that span attributes and events are correctly recorded"""
    session = agentops.start_session(tags=["test-attributes"])
    
    with session.tracer.start_operation("test_operation") as span:
        # Test attributes
        span.set_attribute("string.attr", "test")
        span.set_attribute("int.attr", 42)
        span.set_attribute("bool.attr", True)
        
        # Test events
        span.add_event("test_event", {
            "severity": "INFO",
            "detail": "test detail"
        })
        
        # Verify attributes and events
        assert span.attributes["string.attr"] == "test"
        assert span.attributes["int.attr"] == 42
        assert span.attributes["bool.attr"] is True
        assert len(span.events) > 0

def test_context_propagation():
    """Test that context is correctly propagated across operations"""
    session = agentops.start_session(tags=["test-propagation"])
    
    with session.tracer.start_operation("root_operation") as root_span:
        # Test context injection
        carrier = {}
        session.tracer.inject_context(carrier)
        
        # Verify context was injected
        assert "traceparent" in carrier
        
        # Test context extraction
        context = session.tracer.extract_context(carrier)
        assert context is not None
        assert context.trace_id == root_span.get_span_context().trace_id
