"""Tests for OpenAI response extractors.

This module provides unit tests for the response extractors to ensure
they correctly process both traditional Chat Completion API responses
and the newer Response API format.
"""

import json
from typing import Dict, Any

from agentops.semconv import SpanAttributes, MessageAttributes
from agentops.instrumentation.openai.responses.extractors import (
    extract_from_chat_completion,
    extract_from_response_api,
    detect_response_type,
    extract_from_response,
)


# Sample Chat Completion API response
CHAT_COMPLETION_SAMPLE = {
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1677858242,
    "model": "gpt-4-turbo",
    "system_fingerprint": "fp_12345",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Hello, how can I help you today?",
                "tool_calls": [
                    {
                        "id": "call_12345",
                        "function": {
                            "name": "get_weather",
                            "arguments": "{\"location\":\"San Francisco\",\"unit\":\"celsius\"}"
                        }
                    }
                ]
            },
            "finish_reason": "tool_calls"
        }
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30
    }
}

# Sample Response API response
RESPONSE_API_SAMPLE = {
    "id": "resp_abc123",
    "object": "response",
    "created_at": 1683950300,
    "model": "o1",
    "output": [
        {
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": "Hello! How can I assist you today?"
                }
            ]
        },
        {
            "type": "function",
            "name": "search_database",
            "arguments": "{\"query\": \"weather in San Francisco\"}",
            "id": "func_xyz789"
        }
    ],
    "usage": {
        "input_tokens": 15,
        "output_tokens": 25,
        "total_tokens": 40,
        "output_tokens_details": {
            "reasoning_tokens": 10
        }
    }
}


def test_detect_response_type() -> None:
    """Test the response type detection."""
    assert detect_response_type(CHAT_COMPLETION_SAMPLE) == "chat_completion"
    assert detect_response_type(RESPONSE_API_SAMPLE) == "response_api"
    assert detect_response_type({"foo": "bar"}) == "unknown"


def test_extract_from_chat_completion() -> None:
    """Test extraction from Chat Completion API response."""
    attributes = extract_from_chat_completion(CHAT_COMPLETION_SAMPLE)
    
    # Check metadata
    assert attributes[SpanAttributes.LLM_RESPONSE_MODEL] == "gpt-4-turbo"
    assert attributes[SpanAttributes.LLM_RESPONSE_ID] == "chatcmpl-123"
    assert attributes[SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT] == "fp_12345"
    
    # Check system attribute
    assert attributes[SpanAttributes.LLM_SYSTEM] == "openai"
    
    # Check choice content
    assert attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] == "assistant"
    assert attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] == "Hello, how can I help you today?"
    assert attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] == "tool_calls"
    
    # Check tool calls
    assert attributes[MessageAttributes.TOOL_CALL_ID.format(i=0, j=0)] == "call_12345"
    assert attributes[MessageAttributes.TOOL_CALL_NAME.format(i=0, j=0)] == "get_weather"
    assert attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0, j=0)] == "{\"location\":\"San Francisco\",\"unit\":\"celsius\"}"
    
    # Check usage
    assert attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 10
    assert attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 20
    assert attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 30


def test_extract_from_response_api() -> None:
    """Test extraction from Response API response."""
    attributes = extract_from_response_api(RESPONSE_API_SAMPLE)
    
    # Check metadata
    assert attributes[SpanAttributes.LLM_RESPONSE_MODEL] == "o1"
    assert attributes[SpanAttributes.LLM_RESPONSE_ID] == "resp_abc123"
    
    # Check system attribute
    assert attributes[SpanAttributes.LLM_SYSTEM] == "openai"
    
    # Check message content
    assert attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] == "assistant"
    assert attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] == "Hello! How can I assist you today?"
    
    # Check function content
    assert attributes[MessageAttributes.TOOL_CALL_NAME.format(i=1, j=0)] == "search_database"
    assert attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=1, j=0)] == "{\"query\": \"weather in San Francisco\"}"
    assert attributes[MessageAttributes.TOOL_CALL_ID.format(i=1, j=0)] == "func_xyz789"
    
    # Check usage
    assert attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 15
    assert attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 25
    assert attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 40
    assert attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] == 10


def test_extract_from_response() -> None:
    """Test automatic response type detection and extraction."""
    # Test with Chat Completion API
    chat_attrs = extract_from_response(CHAT_COMPLETION_SAMPLE)
    assert chat_attrs[SpanAttributes.LLM_RESPONSE_MODEL] == "gpt-4-turbo"
    assert MessageAttributes.COMPLETION_CONTENT.format(i=0) in chat_attrs
    
    # Test with Response API
    response_attrs = extract_from_response(RESPONSE_API_SAMPLE)
    assert response_attrs[SpanAttributes.LLM_RESPONSE_MODEL] == "o1"
    assert MessageAttributes.COMPLETION_CONTENT.format(i=0) in response_attrs
    
    # Test with unknown format
    unknown_attrs = extract_from_response({"id": "test", "model": "unknown"})
    assert unknown_attrs[SpanAttributes.LLM_RESPONSE_ID] == "test"
    assert unknown_attrs[SpanAttributes.LLM_RESPONSE_MODEL] == "unknown"
    assert unknown_attrs[SpanAttributes.LLM_SYSTEM] == "openai"


if __name__ == "__main__":
    """Run the tests when the module is executed directly."""
    test_detect_response_type()
    test_extract_from_chat_completion()
    test_extract_from_response_api()
    test_extract_from_response()
    
    print("All tests passed!")