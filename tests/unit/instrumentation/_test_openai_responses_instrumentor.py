"""
Tests for OpenAI Responses Instrumentor

This module tests the instrumentor for OpenAI API responses, ensuring
it properly handles both legacy and modern API response formats.
"""

import json
from typing import Dict, Any
from unittest.mock import patch, MagicMock

import pytest
from opentelemetry import trace

from agentops.semconv import SpanAttributes, MessageAttributes
from agentops.instrumentation.openai import OpenAIResponsesInstrumentor
from agentops.instrumentation.openai import process_token_usage
from agentops.instrumentation.openai.responses.extractors import (
    extract_from_response,
    extract_from_chat_completion,
    extract_from_response_api,
)

# Sample API responses for testing
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
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30
    }
}

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


class TestOpenAIResponsesInstrumentor:
    """Test the OpenAI Responses instrumentor."""
    
    def test_instrumentor_initialization(self):
        """Test that the instrumentor can be initialized."""
        instrumentor = OpenAIResponsesInstrumentor()
        assert instrumentor is not None
        assert instrumentor.instrumentation_dependencies() == ["openai >= 0.27.0"]
    
    def test_token_processing(self):
        """Test token mapping functionality using our shared utility."""
        # Create a usage dictionary that mimics the Response API format
        usage = {
            "input_tokens": 10,
            "output_tokens": 8,
            "total_tokens": 18,
            "output_tokens_details": {
                "reasoning_tokens": 2
            }
        }
        
        # Dictionary to collect the attributes
        attributes = {}
        
        # Process the usage object with our utility
        process_token_usage(usage, attributes)
        
        # Assert that the attributes are correctly set
        assert SpanAttributes.LLM_USAGE_PROMPT_TOKENS in attributes
        assert attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 10
        
        assert SpanAttributes.LLM_USAGE_COMPLETION_TOKENS in attributes
        assert attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 8
        
        assert SpanAttributes.LLM_USAGE_TOTAL_TOKENS in attributes
        assert attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 18
        
        assert f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.reasoning" in attributes
        assert attributes[f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.reasoning"] == 2
    
    def test_extract_from_chat_completion(self):
        """Test extraction from Chat Completion API response."""
        attributes = extract_from_chat_completion(CHAT_COMPLETION_SAMPLE)
        
        # Check metadata
        assert attributes[SpanAttributes.LLM_RESPONSE_MODEL] == "gpt-4-turbo"
        assert attributes[SpanAttributes.LLM_RESPONSE_ID] == "chatcmpl-123"
        
        # Check usage
        assert attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 10
        assert attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 20
        assert attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 30
    
    def test_extract_from_response_api(self):
        """Test extraction from Response API response."""
        attributes = extract_from_response_api(RESPONSE_API_SAMPLE)
        
        # Check metadata
        assert attributes[SpanAttributes.LLM_RESPONSE_MODEL] == "o1"
        assert attributes[SpanAttributes.LLM_RESPONSE_ID] == "resp_abc123"
        
        # Check usage
        assert attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 15
        assert attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 25
        assert attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 40
        assert attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] == 10
    
    def test_instrumentor_init(self):
        """Test that the instrumentor can be initialized."""
        # Simply test that the instrumentor can be created and has the right dependencies
        instrumentor = OpenAIResponsesInstrumentor()
        assert instrumentor.instrumentation_dependencies() == ["openai >= 0.27.0"]
        
    def test_instrument_uninstrument(self):
        """Test simple instrumentor instrument/uninstrument without checking patching"""
        # Just verify we can call instrument and uninstrument without errors
        instrumentor = OpenAIResponsesInstrumentor()
        instrumentor.instrument()
        instrumentor.uninstrument()
    
    def test_extract_from_response(self):
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
    test_instance = TestOpenAIResponsesInstrumentor()
    test_instance.test_instrumentor_initialization()
    test_instance.test_token_processing()
    test_instance.test_extract_from_chat_completion()
    test_instance.test_extract_from_response_api()
    test_instance.test_instrumentor_patching()
    test_instance.test_extract_from_response()
    
    print("All tests passed!")