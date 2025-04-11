import pytest
from unittest.mock import patch, MagicMock, ANY
from opentelemetry.trace import SpanKind

from agentops.instrumentation.anthropic.instrumentor import AnthropicInstrumentor
from agentops.instrumentation.anthropic import LIBRARY_NAME, LIBRARY_VERSION
from agentops.semconv import Meters, SpanAttributes, LLMRequestTypeValues

def test_instrumentor_initialization():
    """Test that the instrumentor initializes with correct dependencies."""
    instrumentor = AnthropicInstrumentor()
    assert isinstance(instrumentor, AnthropicInstrumentor)
    assert instrumentor.instrumentation_dependencies() == ["anthropic >= 0.7.0"]

def test_instrumentor_setup(mock_tracer, mock_meter):
    """Test that the instrumentor properly sets up tracers and meters with correct
    configuration and attributes."""
    instrumentor = AnthropicInstrumentor()
    
    with patch("agentops.instrumentation.anthropic.instrumentor.get_tracer", return_value=mock_tracer) as mock_get_tracer, \
         patch("agentops.instrumentation.anthropic.instrumentor.get_meter", return_value=mock_meter) as mock_get_meter:
        
        instrumentor._instrument()
        
        mock_get_tracer.assert_called_with(LIBRARY_NAME, LIBRARY_VERSION, None)
        mock_get_meter.assert_called_with(LIBRARY_NAME, LIBRARY_VERSION, None)

def test_instrumentor_wraps_methods(mock_tracer, mock_meter):
    """Test that the instrumentor correctly wraps both standard and streaming methods
    with proper instrumentation."""
    instrumentor = AnthropicInstrumentor()
    mock_wrap = MagicMock()
    
    with patch("agentops.instrumentation.anthropic.instrumentor.get_tracer", return_value=mock_tracer), \
         patch("agentops.instrumentation.anthropic.instrumentor.get_meter", return_value=mock_meter), \
         patch("agentops.instrumentation.anthropic.instrumentor.wrap", mock_wrap), \
         patch("agentops.instrumentation.anthropic.instrumentor.wrap_function_wrapper") as mock_wrap_function:
        
        instrumentor._instrument()
        
        assert mock_wrap.call_count == 4
        
        mock_wrap_function.assert_any_call(
            "anthropic.resources.messages.messages",
            "Messages.stream",
            ANY
        )
        mock_wrap_function.assert_any_call(
            "anthropic.resources.messages.messages",
            "AsyncMessages.stream",
            ANY
        )

def test_instrumentor_uninstrument(mock_tracer, mock_meter):
    """Test that the instrumentor properly unwraps all instrumented methods and
    cleans up resources."""
    instrumentor = AnthropicInstrumentor()
    mock_unwrap = MagicMock()
    
    with patch("agentops.instrumentation.anthropic.instrumentor.get_tracer", return_value=mock_tracer), \
         patch("agentops.instrumentation.anthropic.instrumentor.get_meter", return_value=mock_meter), \
         patch("agentops.instrumentation.anthropic.instrumentor.unwrap", mock_unwrap), \
         patch("opentelemetry.instrumentation.utils.unwrap") as mock_otel_unwrap:
        
        instrumentor._uninstrument()
        
        assert mock_unwrap.call_count == 4
        
        mock_otel_unwrap.assert_any_call(
            "anthropic.resources.messages.messages",
            "Messages.stream"
        )
        mock_otel_unwrap.assert_any_call(
            "anthropic.resources.messages.messages",
            "AsyncMessages.stream"
        )

def test_instrumentor_handles_missing_methods(mock_tracer, mock_meter):
    """Test that the instrumentor gracefully handles missing or inaccessible methods
    without raising exceptions."""
    instrumentor = AnthropicInstrumentor()
    mock_wrap = MagicMock(side_effect=AttributeError)
    mock_wrap_function = MagicMock(side_effect=AttributeError)
    
    with patch("agentops.instrumentation.anthropic.instrumentor.get_tracer", return_value=mock_tracer), \
         patch("agentops.instrumentation.anthropic.instrumentor.get_meter", return_value=mock_meter), \
         patch("agentops.instrumentation.anthropic.instrumentor.wrap", mock_wrap), \
         patch("wrapt.wrap_function_wrapper", mock_wrap_function):
        
        instrumentor._instrument()
        instrumentor._uninstrument() 