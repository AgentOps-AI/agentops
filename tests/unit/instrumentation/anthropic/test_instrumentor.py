from unittest.mock import patch, MagicMock, ANY

from agentops.instrumentation.providers.anthropic.instrumentor import AnthropicInstrumentor
from agentops.instrumentation.providers.anthropic import LIBRARY_NAME, LIBRARY_VERSION


def test_instrumentor_initialization():
    """Test that the instrumentor initializes with correct dependencies."""
    instrumentor = AnthropicInstrumentor()
    assert isinstance(instrumentor, AnthropicInstrumentor)
    assert instrumentor.instrumentation_dependencies() == ["anthropic >= 0.7.0"]


def test_instrumentor_setup(mock_tracer, mock_meter):
    """Test that the instrumentor properly sets up tracers and meters with correct
    configuration and attributes."""
    instrumentor = AnthropicInstrumentor()

    with (
        patch("agentops.instrumentation.common.instrumentor.get_tracer", return_value=mock_tracer) as mock_get_tracer,
        patch("agentops.instrumentation.common.instrumentor.get_meter", return_value=mock_meter) as mock_get_meter,
    ):
        # Call _instrument - this is when get_tracer and get_meter are called
        instrumentor._instrument()

        # Verify tracer and meter were requested with correct params
        mock_get_tracer.assert_called_with(LIBRARY_NAME, LIBRARY_VERSION, None)
        mock_get_meter.assert_called_with(LIBRARY_NAME, LIBRARY_VERSION, None)

        # Verify they were stored correctly
        assert instrumentor._tracer == mock_tracer
        assert instrumentor._meter == mock_meter


def test_instrumentor_wraps_methods(mock_tracer, mock_meter):
    """Test that the instrumentor correctly wraps both standard and streaming methods
    with proper instrumentation."""
    instrumentor = AnthropicInstrumentor()

    # Mock the anthropic module structure to prevent import errors
    mock_anthropic = MagicMock()
    mock_messages_module = MagicMock()
    mock_completions_module = MagicMock()

    # Set up the class structure
    mock_messages_module.Messages = MagicMock()
    mock_messages_module.AsyncMessages = MagicMock()
    mock_completions_module.Completions = MagicMock()
    mock_completions_module.AsyncCompletions = MagicMock()

    with (
        patch.dict(
            "sys.modules",
            {
                "anthropic": mock_anthropic,
                "anthropic.resources": mock_anthropic.resources,
                "anthropic.resources.messages": mock_messages_module,
                "anthropic.resources.completions": mock_completions_module,
                "anthropic.resources.messages.messages": mock_messages_module,
            },
        ),
        patch("agentops.instrumentation.common.instrumentor.get_tracer", return_value=mock_tracer),
        patch("agentops.instrumentation.common.instrumentor.get_meter", return_value=mock_meter),
        patch("agentops.instrumentation.common.wrappers.wrap_function_wrapper") as mock_wrap_function,
        patch("agentops.instrumentation.providers.anthropic.instrumentor.wrap_function_wrapper") as mock_stream_wrap,
    ):
        instrumentor._instrument()

        # The base instrumentor will call wrap_function_wrapper for each wrapped method
        assert mock_wrap_function.call_count == 4

        # Check that streaming methods were wrapped with custom wrappers
        mock_stream_wrap.assert_any_call("anthropic.resources.messages.messages", "Messages.stream", ANY)
        mock_stream_wrap.assert_any_call("anthropic.resources.messages.messages", "AsyncMessages.stream", ANY)


def test_instrumentor_uninstrument(mock_tracer, mock_meter):
    """Test that the instrumentor properly unwraps all instrumented methods and
    cleans up resources."""
    instrumentor = AnthropicInstrumentor()
    mock_unwrap = MagicMock()

    # Mock the anthropic module structure
    mock_anthropic = MagicMock()
    mock_messages_module = MagicMock()
    mock_completions_module = MagicMock()

    # Set up the class structure
    mock_messages_module.Messages = MagicMock()
    mock_messages_module.AsyncMessages = MagicMock()
    mock_completions_module.Completions = MagicMock()
    mock_completions_module.AsyncCompletions = MagicMock()

    with (
        patch.dict(
            "sys.modules",
            {
                "anthropic": mock_anthropic,
                "anthropic.resources": mock_anthropic.resources,
                "anthropic.resources.messages": mock_messages_module,
                "anthropic.resources.completions": mock_completions_module,
                "anthropic.resources.messages.messages": mock_messages_module,
            },
        ),
        patch("agentops.instrumentation.common.instrumentor.get_tracer", return_value=mock_tracer),
        patch("agentops.instrumentation.common.instrumentor.get_meter", return_value=mock_meter),
        patch("agentops.instrumentation.common.instrumentor.unwrap", mock_unwrap),  # Patch where it's imported
        patch(
            "agentops.instrumentation.providers.anthropic.instrumentor.otel_unwrap"
        ) as mock_otel_unwrap,  # Patch in anthropic module
        patch("agentops.instrumentation.common.wrappers.wrap_function_wrapper"),
        patch("agentops.instrumentation.providers.anthropic.instrumentor.wrap_function_wrapper"),
    ):
        # Instrument first
        instrumentor._instrument()

        # Now uninstrument
        instrumentor._uninstrument()

        # Should unwrap all 4 configured methods
        assert mock_unwrap.call_count == 4

        # Should also unwrap the custom stream methods
        mock_otel_unwrap.assert_any_call("anthropic.resources.messages.messages", "Messages.stream")
        mock_otel_unwrap.assert_any_call("anthropic.resources.messages.messages", "AsyncMessages.stream")


def test_instrumentor_handles_missing_methods(mock_tracer, mock_meter):
    """Test that the instrumentor gracefully handles missing or inaccessible methods
    without raising exceptions."""
    instrumentor = AnthropicInstrumentor()
    mock_wrap = MagicMock(side_effect=AttributeError)
    mock_wrap_function = MagicMock(side_effect=AttributeError)

    with (
        patch("agentops.instrumentation.common.instrumentor.get_tracer", return_value=mock_tracer),
        patch("agentops.instrumentation.common.instrumentor.get_meter", return_value=mock_meter),
        patch("agentops.instrumentation.common.wrappers.wrap", mock_wrap),
        patch("agentops.instrumentation.providers.anthropic.instrumentor.wrap_function_wrapper", mock_wrap_function),
    ):
        # Should not raise exceptions even when wrapping fails
        instrumentor._instrument()
        instrumentor._uninstrument()
