import pytest
from unittest.mock import MagicMock
from opentelemetry.trace import SpanKind

from agentops.instrumentation.providers.anthropic.stream_wrapper import (
    messages_stream_wrapper,
    messages_stream_async_wrapper,
    AsyncStreamContextManagerWrapper,
)
from agentops.semconv import SpanAttributes, LLMRequestTypeValues, CoreAttributes, MessageAttributes


def test_sync_stream_wrapper(mock_tracer, mock_stream_manager):
    """Test the synchronous stream wrapper functionality including span creation,
    context manager behavior, and token counting."""
    wrapper = messages_stream_wrapper(mock_tracer)
    wrapped = MagicMock(return_value=mock_stream_manager)
    result = wrapper(wrapped, None, [], {})

    assert hasattr(result, "__enter__")
    assert hasattr(result, "__exit__")

    mock_tracer.start_span.assert_called_with(
        "anthropic.messages.stream",
        kind=SpanKind.CLIENT,
        attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
    )

    span = mock_tracer.start_span.return_value
    with result as stream:
        assert span.set_attribute.called
        text = list(stream.text_stream)
        assert len(text) == 5
        assert span.set_attribute.call_count > 0


def test_async_stream_wrapper(mock_tracer, mock_async_stream_manager):
    """Test the asynchronous stream wrapper functionality including span creation
    and proper async context manager setup."""
    wrapper = messages_stream_async_wrapper(mock_tracer)
    wrapped = MagicMock(return_value=mock_async_stream_manager)
    result = wrapper(wrapped, None, [], {})

    assert isinstance(result, AsyncStreamContextManagerWrapper)

    mock_tracer.start_span.assert_called_with(
        "anthropic.messages.stream",
        kind=SpanKind.CLIENT,
        attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
    )


@pytest.mark.asyncio
async def test_async_stream_context_manager(mock_tracer, mock_async_stream_manager):
    """Test the async stream context manager functionality including token counting
    and attribute setting."""
    wrapper = messages_stream_async_wrapper(mock_tracer)
    wrapped = MagicMock(return_value=mock_async_stream_manager)
    result = wrapper(wrapped, None, [], {})

    async with result as stream:
        span = mock_tracer.start_span.return_value
        assert span.set_attribute.called

        text = []
        async for chunk in stream.text_stream:
            text.append(chunk)
        assert len(text) == 5
        assert span.set_attribute.call_count > 0


def test_stream_error_handling(mock_tracer):
    """Test error handling in stream wrapper including exception recording and
    attribute setting."""
    wrapper = messages_stream_wrapper(mock_tracer)
    wrapped = MagicMock(side_effect=Exception("Test error"))

    with pytest.raises(Exception):
        wrapper(wrapped, None, [], {})

    span = mock_tracer.start_span.return_value
    span.record_exception.assert_called()
    span.set_attribute.assert_any_call(CoreAttributes.ERROR_MESSAGE, "Test error")
    span.set_attribute.assert_any_call(CoreAttributes.ERROR_TYPE, "Exception")
    span.end.assert_called()


def test_stream_with_event_handler(mock_tracer, mock_stream_manager, mock_event_handler):
    """Test stream wrapper with event handler including proper event forwarding
    and handler integration."""
    wrapper = messages_stream_wrapper(mock_tracer)
    wrapped = MagicMock(return_value=mock_stream_manager)
    result = wrapper(wrapped, None, [], {"event_handler": mock_event_handler})

    assert hasattr(result, "__enter__")
    assert hasattr(result, "__exit__")

    with result as stream:
        text = list(stream.text_stream)
        assert len(text) == 5
        assert mock_event_handler.on_text_delta.call_count > 0


def test_stream_final_message_attributes(mock_tracer, mock_stream_manager):
    """Test that final message attributes are properly captured and set on the span."""
    wrapper = messages_stream_wrapper(mock_tracer)
    wrapped = MagicMock(return_value=mock_stream_manager)

    final_message = MagicMock()
    final_message.content = [MagicMock(text="Final response")]
    final_message.usage = MagicMock(input_tokens=10, output_tokens=20)
    mock_stream_manager._MessageStreamManager__stream._MessageStream__final_message_snapshot = final_message

    result = wrapper(wrapped, None, [], {})

    with result as stream:
        list(stream.text_stream)

    span = mock_tracer.start_span.return_value
    span.set_attribute.assert_any_call(MessageAttributes.COMPLETION_TYPE.format(i=0), "text")
    span.set_attribute.assert_any_call(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")
    span.set_attribute.assert_any_call(MessageAttributes.COMPLETION_CONTENT.format(i=0), "Final response")
    span.set_attribute.assert_any_call(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, 10)
    span.set_attribute.assert_any_call(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, 20)
    span.set_attribute.assert_any_call(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, 30)
