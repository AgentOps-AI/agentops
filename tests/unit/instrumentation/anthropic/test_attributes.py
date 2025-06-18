"""Tests for Anthropic attribute extraction functionality."""

from agentops.semconv import (
    InstrumentationAttributes,
    SpanAttributes,
    MessageAttributes,
    ToolAttributes,
    ToolStatus,
)
from agentops.instrumentation.providers.anthropic.attributes.common import (
    get_common_instrumentation_attributes,
    extract_request_attributes,
)
from agentops.instrumentation.providers.anthropic.attributes.message import (
    get_message_request_attributes,
    get_stream_attributes,
    get_stream_event_attributes,
)
from agentops.instrumentation.providers.anthropic.attributes.tools import (
    extract_tool_definitions,
    extract_tool_use_blocks,
    get_tool_attributes,
)


# Common Attributes Tests
def test_get_common_instrumentation_attributes():
    """Test extraction of common instrumentation attributes."""
    attributes = get_common_instrumentation_attributes()
    assert attributes[InstrumentationAttributes.LIBRARY_NAME] == "anthropic"
    assert attributes[InstrumentationAttributes.LIBRARY_VERSION] >= "0.49.0"


def test_extract_request_attributes():
    """Test extraction of request attributes from kwargs."""
    kwargs = {"model": "claude-3-opus-20240229", "max_tokens": 100, "temperature": 0.7, "top_p": 0.9, "stream": True}
    attributes = extract_request_attributes(kwargs)
    assert attributes[SpanAttributes.LLM_REQUEST_MODEL] == "claude-3-opus-20240229"
    assert attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] == 100
    assert attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] == 0.7
    assert attributes[SpanAttributes.LLM_REQUEST_TOP_P] == 0.9
    assert attributes[SpanAttributes.LLM_REQUEST_STREAMING] is True


def test_extract_request_attributes_partial():
    """Test extraction of request attributes with partial kwargs."""
    kwargs = {"model": "claude-3-opus-20240229", "temperature": 0.7}
    attributes = extract_request_attributes(kwargs)
    assert attributes[SpanAttributes.LLM_REQUEST_MODEL] == "claude-3-opus-20240229"
    assert attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] == 0.7
    assert SpanAttributes.LLM_REQUEST_MAX_TOKENS not in attributes
    assert SpanAttributes.LLM_REQUEST_TOP_P not in attributes
    assert SpanAttributes.LLM_REQUEST_STREAMING not in attributes


def test_get_message_request_attributes():
    """Test extraction of message request attributes."""
    kwargs = {
        "model": "claude-3-opus-20240229",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
        ],
        "max_tokens": 100,
    }
    attributes = get_message_request_attributes(kwargs)
    assert attributes[SpanAttributes.LLM_REQUEST_MODEL] == "claude-3-opus-20240229"
    assert attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] == 100
    assert MessageAttributes.PROMPT_ROLE.format(i=0) in attributes
    assert MessageAttributes.PROMPT_CONTENT.format(i=0) in attributes
    assert MessageAttributes.PROMPT_ROLE.format(i=1) in attributes
    assert MessageAttributes.PROMPT_CONTENT.format(i=1) in attributes


# Stream Attributes Tests
def test_get_stream_attributes():
    """Test extraction of stream attributes."""

    class MockStream:
        def __init__(self):
            self.model = "claude-3-opus-20240229"

    stream = MockStream()
    attributes = get_stream_attributes(stream)
    assert attributes[SpanAttributes.LLM_REQUEST_STREAMING] is True
    assert attributes[SpanAttributes.LLM_REQUEST_MODEL] == "claude-3-opus-20240229"


def test_get_stream_event_attributes_sequence(mock_stream_event, mock_message_stop_event):
    """Test extraction of attributes from a sequence of stream events."""
    # Test MessageStartEvent
    start_attributes = get_stream_event_attributes(mock_stream_event)
    assert start_attributes[SpanAttributes.LLM_RESPONSE_ID] == "msg_123"
    assert start_attributes[SpanAttributes.LLM_RESPONSE_MODEL] == "claude-3-opus-20240229"
    assert start_attributes[MessageAttributes.COMPLETION_ID.format(i=0)] == "msg_123"

    # Test MessageStopEvent
    stop_attributes = get_stream_event_attributes(mock_message_stop_event)
    assert stop_attributes[SpanAttributes.LLM_RESPONSE_STOP_REASON] == "stop_sequence"
    assert stop_attributes[SpanAttributes.LLM_RESPONSE_FINISH_REASON] == "stop_sequence"
    assert stop_attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] == "stop_sequence"


def test_get_stream_event_attributes_raw_message_start():
    """Test extraction of raw message start event attributes."""

    class MockUsage:
        def __init__(self):
            self.input_tokens = 10
            self.output_tokens = 5

    class MockMessage:
        def __init__(self):
            self.usage = MockUsage()

    class MockRawMessageStartEvent:
        def __init__(self):
            self.message = MockMessage()
            self.__class__.__name__ = "RawMessageStartEvent"

    event = MockRawMessageStartEvent()
    attributes = get_stream_event_attributes(event)

    assert attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 10
    assert attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 5
    assert attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 15


def test_get_stream_event_attributes_raw_message_delta():
    """Test extraction of raw message delta event attributes."""

    class MockDelta:
        def __init__(self):
            self.stop_reason = "end_turn"

    class MockRawMessageDeltaEvent:
        def __init__(self):
            self.delta = MockDelta()
            self.__class__.__name__ = "RawMessageDeltaEvent"

    event = MockRawMessageDeltaEvent()
    attributes = get_stream_event_attributes(event)

    assert attributes[SpanAttributes.LLM_RESPONSE_STOP_REASON] == "end_turn"
    assert attributes[SpanAttributes.LLM_RESPONSE_FINISH_REASON] == "end_turn"
    assert attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] == "end_turn"


# Tool Attributes Tests
def test_extract_tool_definitions(mock_tool_definition):
    """Test extraction of tool definitions."""
    attributes = extract_tool_definitions(mock_tool_definition)
    assert attributes[MessageAttributes.TOOL_CALL_NAME.format(i=0)] == "calculator"
    assert attributes[MessageAttributes.TOOL_CALL_TYPE.format(i=0)] == "function"
    assert attributes[MessageAttributes.TOOL_CALL_DESCRIPTION.format(i=0)] == "A simple calculator"
    tool_args = attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0)]
    assert isinstance(tool_args, str)
    assert "type" in tool_args
    assert "properties" in tool_args
    assert SpanAttributes.LLM_REQUEST_FUNCTIONS in attributes


def test_extract_tool_use_blocks(mock_tool_use_content):
    """Test extraction of tool use blocks."""
    tool_uses = extract_tool_use_blocks(mock_tool_use_content)
    assert tool_uses is not None
    assert len(tool_uses) == 1
    assert tool_uses[0]["name"] == "calculator"
    assert tool_uses[0]["id"] == "tool_123"
    assert tool_uses[0]["input"] == {"operation": "add", "numbers": [1, 2]}


def test_get_tool_attributes(mock_tool_use_content):
    """Test extraction of tool attributes from content."""
    attributes = get_tool_attributes(mock_tool_use_content)
    assert attributes[MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=0)] == "calculator"
    assert attributes[MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=0, j=0)] == "tool_123"
    assert attributes[MessageAttributes.COMPLETION_TOOL_CALL_TYPE.format(i=0, j=0)] == "function"
    tool_args = attributes[MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=0, j=0)]
    assert isinstance(tool_args, str)
    assert "operation" in tool_args
    assert attributes[MessageAttributes.TOOL_CALL_ID.format(i=0)] == "tool_123"
    assert attributes[MessageAttributes.TOOL_CALL_NAME.format(i=0)] == "calculator"
    assert attributes[f"{ToolAttributes.TOOL_STATUS}.0"] == ToolStatus.EXECUTING.value
    assert attributes["anthropic.tool_calls.count"] == 1


def test_get_tool_attributes_empty():
    """Test extraction of tool attributes with empty content."""
    attributes = get_tool_attributes([])
    assert not attributes


def test_get_tool_attributes_mixed_content():
    """Test extraction of tool attributes with mixed content types."""

    class MockTextBlock:
        def __init__(self):
            self.type = "text"
            self.text = "Hello world"

    class MockToolUseBlock:
        def __init__(self):
            self.type = "tool_use"
            self.name = "calculator"
            self.id = "tool_123"
            self.input = {"operation": "add", "numbers": [1, 2]}

    content = [MockTextBlock(), MockToolUseBlock()]
    attributes = get_tool_attributes(content)
    assert MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=0) in attributes
    assert attributes[MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=0)] == "calculator"


def test_get_message_attributes_with_stream(mock_stream_event, mock_message_stop_event):
    """Test extraction of attributes from a Stream object."""

    # Test MessageStartEvent attributes
    start_attributes = get_stream_event_attributes(mock_stream_event)
    assert start_attributes[SpanAttributes.LLM_RESPONSE_ID] == "msg_123"
    assert start_attributes[SpanAttributes.LLM_RESPONSE_MODEL] == "claude-3-opus-20240229"
    assert start_attributes[MessageAttributes.COMPLETION_ID.format(i=0)] == "msg_123"

    # Test MessageStopEvent attributes
    stop_attributes = get_stream_event_attributes(mock_message_stop_event)
    assert stop_attributes[SpanAttributes.LLM_RESPONSE_STOP_REASON] == "stop_sequence"
    assert stop_attributes[SpanAttributes.LLM_RESPONSE_FINISH_REASON] == "stop_sequence"
    assert stop_attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] == "stop_sequence"
