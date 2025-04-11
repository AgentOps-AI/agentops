"""Tests for Anthropic attribute extraction functionality."""

import pytest
from typing import Dict, Any

from agentops.semconv import (
    InstrumentationAttributes,
    SpanAttributes,
    LLMRequestTypeValues,
    MessageAttributes,
    ToolAttributes,
    ToolStatus,
)
from agentops.instrumentation.anthropic.attributes.common import (
    get_common_instrumentation_attributes,
    extract_request_attributes,
)
from agentops.instrumentation.anthropic.attributes.message import (
    get_message_attributes,
    get_message_request_attributes,
    get_message_response_attributes,
    get_stream_attributes,
    get_stream_event_attributes,
)
from agentops.instrumentation.anthropic.attributes.tools import (
    extract_tool_definitions,
    extract_tool_use_blocks,
    get_tool_attributes,
)


# Common Attributes Tests
def test_get_common_instrumentation_attributes():
    """Test extraction of common instrumentation attributes."""
    attributes = get_common_instrumentation_attributes()
    assert attributes[InstrumentationAttributes.LIBRARY_NAME] == "anthropic"
    assert attributes[InstrumentationAttributes.LIBRARY_VERSION] == "0.49.0"


def test_extract_request_attributes():
    """Test extraction of request attributes from kwargs."""
    kwargs = {
        'model': 'claude-3-opus-20240229',
        'max_tokens': 100,
        'temperature': 0.7,
        'top_p': 0.9,
        'stream': True
    }
    attributes = extract_request_attributes(kwargs)
    assert attributes[SpanAttributes.LLM_REQUEST_MODEL] == 'claude-3-opus-20240229'
    assert attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] == 100
    assert attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] == 0.7
    assert attributes[SpanAttributes.LLM_REQUEST_TOP_P] == 0.9
    assert attributes[SpanAttributes.LLM_REQUEST_STREAMING] is True


def test_extract_request_attributes_partial():
    """Test extraction of request attributes with partial kwargs."""
    kwargs = {
        'model': 'claude-3-opus-20240229',
        'temperature': 0.7
    }
    attributes = extract_request_attributes(kwargs)
    assert attributes[SpanAttributes.LLM_REQUEST_MODEL] == 'claude-3-opus-20240229'
    assert attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] == 0.7
    assert SpanAttributes.LLM_REQUEST_MAX_TOKENS not in attributes
    assert SpanAttributes.LLM_REQUEST_TOP_P not in attributes
    assert SpanAttributes.LLM_REQUEST_STREAMING not in attributes


def test_get_message_request_attributes():
    """Test extraction of message request attributes."""
    kwargs = {
        'model': 'claude-3-opus-20240229',
        'messages': [
            {'role': 'system', 'content': 'You are a helpful assistant'},
            {'role': 'user', 'content': 'Hello'}
        ],
        'max_tokens': 100
    }
    attributes = get_message_request_attributes(kwargs)
    assert attributes[SpanAttributes.LLM_REQUEST_MODEL] == 'claude-3-opus-20240229'
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
            self.model = 'claude-3-opus-20240229'
    stream = MockStream()
    attributes = get_stream_attributes(stream)
    assert attributes[SpanAttributes.LLM_REQUEST_STREAMING] is True
    assert attributes[SpanAttributes.LLM_REQUEST_MODEL] == 'claude-3-opus-20240229'


def test_get_stream_event_attributes_start(mock_stream_event):
    """Test extraction of stream start event attributes."""
    attributes = get_stream_event_attributes(mock_stream_event)
    assert attributes[SpanAttributes.LLM_RESPONSE_ID] == 'msg_123'
    assert attributes[SpanAttributes.LLM_RESPONSE_MODEL] == 'claude-3-opus-20240229'
    assert attributes[MessageAttributes.COMPLETION_ID.format(i=0)] == 'msg_123'


def test_get_stream_event_attributes_stop(mock_message_stop_event):
    """Test extraction of stream stop event attributes."""
    attributes = get_stream_event_attributes(mock_message_stop_event)
    assert attributes[SpanAttributes.LLM_RESPONSE_STOP_REASON] == 'stop_sequence'
    assert attributes[SpanAttributes.LLM_RESPONSE_FINISH_REASON] == 'stop_sequence'
    assert attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] == 'stop_sequence'


# Tool Attributes Tests
def test_extract_tool_definitions(mock_tool_definition):
    """Test extraction of tool definitions."""
    attributes = extract_tool_definitions(mock_tool_definition)
    assert attributes[MessageAttributes.TOOL_CALL_NAME.format(i=0)] == 'calculator'
    assert attributes[MessageAttributes.TOOL_CALL_TYPE.format(i=0)] == 'function'
    assert attributes[MessageAttributes.TOOL_CALL_DESCRIPTION.format(i=0)] == 'A simple calculator'
    tool_args = attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0)]
    assert isinstance(tool_args, str)
    assert 'type' in tool_args
    assert 'properties' in tool_args
    assert SpanAttributes.LLM_REQUEST_FUNCTIONS in attributes


def test_extract_tool_use_blocks(mock_tool_use_content):
    """Test extraction of tool use blocks."""
    tool_uses = extract_tool_use_blocks(mock_tool_use_content)
    assert tool_uses is not None
    assert len(tool_uses) == 1
    assert tool_uses[0]['name'] == 'calculator'
    assert tool_uses[0]['id'] == 'tool_123'
    assert tool_uses[0]['input'] == {'operation': 'add', 'numbers': [1, 2]}


def test_get_tool_attributes(mock_tool_use_content):
    """Test extraction of tool attributes from content."""
    attributes = get_tool_attributes(mock_tool_use_content)
    assert attributes[MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=0)] == 'calculator'
    assert attributes[MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=0, j=0)] == 'tool_123'
    assert attributes[MessageAttributes.COMPLETION_TOOL_CALL_TYPE.format(i=0, j=0)] == 'function'
    tool_args = attributes[MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=0, j=0)]
    assert isinstance(tool_args, str)
    assert 'operation' in tool_args
    assert attributes[MessageAttributes.TOOL_CALL_ID.format(i=0)] == 'tool_123'
    assert attributes[MessageAttributes.TOOL_CALL_NAME.format(i=0)] == 'calculator'
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
    assert attributes[MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=0)] == 'calculator' 