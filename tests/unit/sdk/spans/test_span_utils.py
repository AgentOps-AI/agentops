import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import SpanKind, Status, StatusCode

from agentops.sdk.spans.utils import (
    get_root_span,
    get_span_attributes,
    get_current_trace_context,
    is_same_trace,
    set_span_attributes
)
from agentops.sdk.spans.session import SessionSpan
from agentops.sdk.core import TracingCore
from agentops.sdk.types import TracingConfig


def test_get_current_trace_context(instrumentation):
    """Test get_current_trace_context with a real span."""
    # Get a tracer from the instrumentation tester's provider
    tracer = trace.get_tracer("test_tracer")
    
    # Create a span
    with tracer.start_as_current_span("test_span") as span:
        # Get the trace context
        trace_id, span_id = get_current_trace_context()
        
        # Get the actual trace ID and span ID
        context = span.get_span_context()
        actual_trace_id = format(context.trace_id, '032x')
        actual_span_id = format(context.span_id, '016x')
        
        # Verify
        assert trace_id == actual_trace_id
        assert span_id == actual_span_id


def test_is_same_trace(instrumentation):
    """Test is_same_trace with real spans."""
    # Get a tracer from the instrumentation tester's provider
    tracer = trace.get_tracer("test_tracer")
    
    # Clear any existing spans before starting the test
    instrumentation.clear_spans()
    
    # Create two spans in the same trace
    with tracer.start_as_current_span("parent_span") as parent_span:
        with tracer.start_as_current_span("child_span") as child_span:
            # Test is_same_trace
            result = is_same_trace(parent_span, child_span)
            assert result is True
    
    # Force flush any pending spans
    instrumentation.span_processor.force_flush()
    
    # Create a span
    with tracer.start_as_current_span("span1") as span1:
        # End the first span to ensure we get a new trace
        pass
    
    # Force flush any pending spans and clear the current context
    instrumentation.span_processor.force_flush()
    trace.get_current_span().end()  # End any current span
    
    # Create another span in a different trace
    with tracer.start_as_current_span("span2", context=None) as span2:
        # Test is_same_trace with spans in different traces
        result = is_same_trace(span1, span2)
        assert result is False


def test_set_span_attributes(instrumentation):
    """Test set_span_attributes with a real span."""
    # Get a tracer from the instrumentation tester's provider
    tracer = trace.get_tracer("test_tracer")
    
    # Create a span
    with tracer.start_as_current_span("test_span") as span:
        # Set attributes
        set_span_attributes(
            string_attr="string_value",
            int_attr=123,
            float_attr=123.45,
            bool_attr=True,
            list_attr=["a", "b", "c"]
        )
        
        # Get the attributes using get_span_attributes
        attributes = get_span_attributes(span)
        
        # Verify
        assert attributes["string_attr"] == "string_value"
        assert attributes["int_attr"] == 123
        assert attributes["float_attr"] == 123.45
        assert attributes["bool_attr"] is True
        
        # The list might be converted to a tuple in the span attributes
        assert list(attributes["list_attr"]) == ["a", "b", "c"]
        assert "none_attr" not in attributes


def test_get_span_attributes(instrumentation):
    """Test get_span_attributes with a real span."""
    # Get a tracer from the instrumentation tester's provider
    tracer = trace.get_tracer("test_tracer")
    
    # Create a span with attributes
    with tracer.start_as_current_span("test_span") as span:
        # Set some attributes
        span.set_attribute("key1", "value1")
        span.set_attribute("key2", 123)
        
        # Get the attributes using our utility function
        attributes = get_span_attributes(span)
        
        # Verify
        assert attributes["key1"] == "value1"
        assert attributes["key2"] == 123
        
        # Test with current span
        current_attributes = get_span_attributes()
        assert current_attributes["key1"] == "value1"
        assert current_attributes["key2"] == 123


def test_get_root_span(instrumentation):
    """Test get_root_span with nested spans."""
    # Get a tracer from the instrumentation tester's provider
    tracer = trace.get_tracer("test_tracer")
    
    # Create a parent span
    with tracer.start_as_current_span("root_span") as root_span:
        # Create a child span
        with tracer.start_as_current_span("child_span") as child_span:
            # Create a grandchild span
            with tracer.start_as_current_span("grandchild_span") as grandchild_span:
                # Test get_root_span with the grandchild span
                # Note: In a real application with SessionSpan, this would return the SessionSpan
                # But in this test environment, we don't have a SessionSpan, so it returns None
                result = get_root_span(grandchild_span)
                
                # Since we're not using a real SessionSpan, we expect None
                # In a real application, this would return the root SessionSpan
                assert result is None
                
                # Test get_root_span with the current span (grandchild)
                current_result = get_root_span()
                assert current_result is None 