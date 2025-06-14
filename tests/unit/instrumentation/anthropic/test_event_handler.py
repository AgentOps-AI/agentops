from unittest.mock import MagicMock
from opentelemetry.trace import Span

from agentops.instrumentation.providers.anthropic.event_handler_wrapper import EventHandleWrapper
from agentops.semconv import CoreAttributes


def test_event_handler_initialization():
    """Test that event handler initializes correctly with a span and no original handler."""
    span = MagicMock(spec=Span)
    handler = EventHandleWrapper(None, span)
    assert handler._span == span
    assert handler._original_handler is None


def test_event_handler_with_original_handler():
    """Test that event handler properly stores the original handler reference."""
    original_handler = MagicMock()
    span = MagicMock(spec=Span)
    handler = EventHandleWrapper(original_handler, span)
    assert handler._original_handler == original_handler


def test_event_forwarding():
    """Test that all event types are correctly forwarded to the original handler
    while maintaining the original event data."""
    original_handler = MagicMock()
    span = MagicMock(spec=Span)
    handler = EventHandleWrapper(original_handler, span)

    event = {"type": "test"}
    handler.on_event(event)
    original_handler.on_event.assert_called_with(event)

    delta = {"text": "test"}
    snapshot = {"content": "test"}
    handler.on_text_delta(delta, snapshot)
    original_handler.on_text_delta.assert_called_with(delta, snapshot)

    content_block = {"type": "text"}
    handler.on_content_block_start(content_block)
    original_handler.on_content_block_start.assert_called_with(content_block)


def test_event_handler_without_original_handler():
    """Test that event handler gracefully handles events when no original handler
    is provided, ensuring no exceptions are raised."""
    span = MagicMock(spec=Span)
    handler = EventHandleWrapper(None, span)

    handler.on_event({})
    handler.on_text_delta({}, {})
    handler.on_content_block_start({})


def test_error_handling():
    """Test that errors are properly recorded in the span and forwarded to the
    original handler with correct error attributes."""
    original_handler = MagicMock()
    span = MagicMock(spec=Span)
    handler = EventHandleWrapper(original_handler, span)

    error = Exception("Test error")
    handler.on_error(error)

    span.record_exception.assert_called_with(error)
    span.set_attribute.assert_any_call(CoreAttributes.ERROR_MESSAGE, "Test error")
    span.set_attribute.assert_any_call(CoreAttributes.ERROR_TYPE, "Exception")
    original_handler.on_error.assert_called_with(error)


def test_error_handling_without_original_handler():
    """Test that errors are properly recorded in the span even when no original
    handler is present."""
    span = MagicMock(spec=Span)
    handler = EventHandleWrapper(None, span)

    error = Exception("Test error")
    handler.on_error(error)

    span.record_exception.assert_called_with(error)
    span.set_attribute.assert_any_call(CoreAttributes.ERROR_MESSAGE, "Test error")
    span.set_attribute.assert_any_call(CoreAttributes.ERROR_TYPE, "Exception")


def test_error_in_original_handler():
    """Test that errors from the original handler are caught and logged without
    disrupting the event handling flow."""
    original_handler = MagicMock()
    original_handler.on_event.side_effect = Exception("Handler error")
    span = MagicMock(spec=Span)
    handler = EventHandleWrapper(original_handler, span)

    handler.on_event({})
    assert original_handler.on_event.called
