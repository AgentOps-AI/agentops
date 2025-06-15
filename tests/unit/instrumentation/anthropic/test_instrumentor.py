import pytest
from unittest.mock import MagicMock, patch

from agentops.instrumentation.providers.anthropic.instrumentor import AnthropicInstrumentor


def test_instrumentor_initialization():
    """Test basic instrumentor initialization."""
    instrumentor = AnthropicInstrumentor()
    assert instrumentor is not None
    assert instrumentor.get_library_name() == "anthropic"
    # The version comes from the actual library, just verify it's a string
    assert isinstance(instrumentor.get_library_version(), str)


def test_instrumentor_setup():
    """Test that the instrumentor sets up correct wrapped methods."""
    instrumentor = AnthropicInstrumentor()

    # Check that wrapped methods are initialized
    wrapped_methods = instrumentor.get_wrapped_methods()
    assert len(wrapped_methods) > 0

    # Verify Messages.create is wrapped
    messages_create = next(
        (m for m in wrapped_methods if m.class_name == "Messages" and m.method_name == "create"), None
    )
    assert messages_create is not None
    assert messages_create.trace_name == "anthropic.messages.create"


def test_instrumentor_wraps_methods():
    """Test that the instrumentor properly wraps methods."""
    instrumentor = AnthropicInstrumentor()

    # Patch at the base class level where _wrap_method is called
    with patch.object(instrumentor, "_wrap_method") as mock_wrap_method:
        # Create a mock tracer provider
        mock_tracer_provider = MagicMock()

        # Instrument
        instrumentor._instrument(tracer_provider=mock_tracer_provider)

        # Verify _wrap_method was called for each wrapped method
        assert mock_wrap_method.call_count == len(instrumentor.get_wrapped_methods())


def test_instrumentor_uninstrument():
    """Test that the instrumentor can properly uninstrument."""
    instrumentor = AnthropicInstrumentor()

    # Patch at the base class level where _unwrap_method is called
    with patch.object(instrumentor, "_unwrap_method") as mock_unwrap_method:
        # First instrument
        mock_tracer_provider = MagicMock()
        instrumentor._instrument(tracer_provider=mock_tracer_provider)

        # Then uninstrument
        instrumentor._uninstrument()

        # Verify _unwrap_method was called for each wrapped method
        assert mock_unwrap_method.call_count == len(instrumentor.get_wrapped_methods())


def test_instrumentor_handles_missing_methods():
    """Test that the instrumentor handles missing methods gracefully."""
    instrumentor = AnthropicInstrumentor()

    # The base class _wrap_method already handles errors, so we test that
    # instrumentation works even if some methods are missing
    mock_tracer_provider = MagicMock()

    # This should not raise an exception even if some methods don't exist
    try:
        instrumentor._instrument(tracer_provider=mock_tracer_provider)
    except Exception as e:
        pytest.fail(f"Instrumentor should handle missing methods gracefully, but raised: {e}")


def test_streaming_methods():
    """Test that streaming methods are properly configured."""
    instrumentor = AnthropicInstrumentor()

    # Get streaming methods
    streaming_methods = instrumentor.get_streaming_methods()

    # Should have Messages stream methods
    assert len(streaming_methods) == 2

    # Check sync stream method
    sync_stream = next((m for m in streaming_methods if "AsyncMessages" not in m["class_method"]), None)
    assert sync_stream is not None
    assert "Messages.stream" in sync_stream["class_method"]

    # Check async stream method
    async_stream = next((m for m in streaming_methods if "AsyncMessages" in m["class_method"]), None)
    assert async_stream is not None
    assert "AsyncMessages.stream" in async_stream["class_method"]
