"""
Tests for OpenAI Chat Completion API Serialization

This module contains tests for properly handling and serializing the traditional OpenAI Chat Completion API format.

Important distinction:
- OpenAI Chat Completion API: The traditional OpenAI API format that uses the "ChatCompletion" 
  class with a "choices" array containing messages.

- OpenAI Response API: Used exclusively by the OpenAI Agents SDK, these objects use 
  the "Response" class with an "output" array containing messages and their content.

This separation ensures we correctly implement attribute extraction for both formats
in our instrumentation.
"""
import json
from typing import Any, Dict, List, Optional, Union

import pytest
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from agentops.logging import logger

from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice, CompletionUsage
from openai.types.chat.chat_completion_message import FunctionCall
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)


import agentops
from agentops.sdk.core import TracingCore
from agentops.semconv import SpanAttributes
from tests.unit.sdk.instrumentation_tester import InstrumentationTester
from third_party.opentelemetry.instrumentation.agents.agentops_agents_instrumentor import AgentsDetailedExporter
from tests.unit.instrumentation.mock_span import MockSpan, process_with_instrumentor


# Standard ChatCompletion response
OPENAI_CHAT_COMPLETION = ChatCompletion(
    id="chatcmpl-123",
    model="gpt-4-0125-preview",
    choices=[
        Choice(
            index=0,
            message=ChatCompletionMessage(
                role="assistant",
                content="This is a test response."
            ),
            finish_reason="stop"
        )
    ],
    usage=CompletionUsage(
        prompt_tokens=10,
        completion_tokens=8,
        total_tokens=18
    ),
    system_fingerprint="fp_44f3",
    object="chat.completion",
    created=1677858242
)

# ChatCompletion with tool calls
OPENAI_CHAT_COMPLETION_WITH_TOOL_CALLS = ChatCompletion(
    id="chatcmpl-456",
    model="gpt-4-0125-preview",
    choices=[
        Choice(
            index=0,
            message=ChatCompletionMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    ChatCompletionMessageToolCall(
                        id="call_abc123",
                        type="function",
                        function=Function(
                            name="get_weather",
                            arguments='{"location": "San Francisco", "unit": "celsius"}'
                        )
                    )
                ]
            ),
            finish_reason="tool_calls"
        )
    ],
    usage=CompletionUsage(
        prompt_tokens=12,
        completion_tokens=10,
        total_tokens=22
    ),
    system_fingerprint="fp_55g4",
    object="chat.completion",
    created=1677858243
)

# ChatCompletion with function call (for older OpenAI models)
OPENAI_CHAT_COMPLETION_WITH_FUNCTION_CALL = ChatCompletion(
    id="chatcmpl-789",
    model="gpt-3.5-turbo",
    choices=[
        Choice(
            index=0,
            message=ChatCompletionMessage(
                role="assistant",
                content=None,
                function_call=FunctionCall(
                    name="get_stock_price",
                    arguments='{"symbol": "AAPL"}'
                )
            ),
            finish_reason="function_call"
        )
    ],
    usage=CompletionUsage(
        prompt_tokens=8,
        completion_tokens=6,
        total_tokens=14
    ),
    object="chat.completion",
    created=1677858244
)


# Test reference: Expected span attributes from processing a standard ChatCompletion object
#
# This dictionary defines precisely what span attributes we expect our instrumentor
# to produce when processing a standard ChatCompletion object.
EXPECTED_CHAT_COMPLETION_SPAN_ATTRIBUTES = {
    # Basic response metadata
    "gen_ai.response.model": "gpt-4-0125-preview",
    "gen_ai.response.id": "chatcmpl-123",
    "gen_ai.openai.system_fingerprint": "fp_44f3",
    
    # Token usage metrics
    "gen_ai.usage.total_tokens": 18,
    "gen_ai.usage.prompt_tokens": 10,
    "gen_ai.usage.completion_tokens": 8,
    
    # Content extraction from Chat Completion API format
    "gen_ai.completion.0.content": "This is a test response.",
    "gen_ai.completion.0.role": "assistant",
    "gen_ai.completion.0.finish_reason": "stop",
    
    # Standard OpenTelemetry attributes
    "trace.id": "trace123",
    "span.id": "span456",
    "parent.id": "parent789",
    "library.name": "agents-sdk",
    "library.version": "0.1.0"
}

# Test reference: Expected span attributes from processing a ChatCompletion with tool calls
EXPECTED_TOOL_CALLS_SPAN_ATTRIBUTES = {
    # Basic response metadata
    "gen_ai.response.model": "gpt-4-0125-preview",
    "gen_ai.response.id": "chatcmpl-456",
    "gen_ai.openai.system_fingerprint": "fp_55g4",
    
    # Token usage metrics
    "gen_ai.usage.total_tokens": 22,
    "gen_ai.usage.prompt_tokens": 12,
    "gen_ai.usage.completion_tokens": 10,
    
    # Completion metadata
    "gen_ai.completion.0.role": "assistant",
    "gen_ai.completion.0.finish_reason": "tool_calls",
    
    # Tool call details
    "gen_ai.completion.0.tool_calls.0.id": "call_abc123",
    "gen_ai.completion.0.tool_calls.0.name": "get_weather",
    "gen_ai.completion.0.tool_calls.0.arguments": '{"location": "San Francisco", "unit": "celsius"}',
    
    # Standard OpenTelemetry attributes
    "trace.id": "trace123",
    "span.id": "span456",
    "parent.id": "parent789",
    "library.name": "agents-sdk",
    "library.version": "0.1.0"
}

# Test reference: Expected span attributes from processing a ChatCompletion with function call
EXPECTED_FUNCTION_CALL_SPAN_ATTRIBUTES = {
    # Basic response metadata
    "gen_ai.response.model": "gpt-3.5-turbo",
    "gen_ai.response.id": "chatcmpl-789",
    
    # Token usage metrics
    "gen_ai.usage.total_tokens": 14,
    "gen_ai.usage.prompt_tokens": 8,
    "gen_ai.usage.completion_tokens": 6,
    
    # Completion metadata
    "gen_ai.completion.0.role": "assistant",
    "gen_ai.completion.0.finish_reason": "function_call",
    
    # Function call details
    "gen_ai.completion.0.function_call.name": "get_stock_price",
    "gen_ai.completion.0.function_call.arguments": '{"symbol": "AAPL"}',
    
    # Standard OpenTelemetry attributes
    "trace.id": "trace123",
    "span.id": "span456",
    "parent.id": "parent789",
    "library.name": "agents-sdk",
    "library.version": "0.1.0"
}


class TestModelResponseSerialization:
    """Tests for model response serialization in spans"""

    @pytest.fixture
    def instrumentation(self):
        """Set up instrumentation for tests"""
        return InstrumentationTester()

    def test_openai_chat_completion_serialization(self, instrumentation):
        """Test serialization of standard OpenAI ChatCompletion using the actual instrumentor"""
        # Dictionary to capture attributes from the instrumentor
        captured_attributes = {}
        
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span for our test
        with tracer.start_as_current_span("test_chat_completion_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "llm")
            
            # Create a mock span with the ChatCompletion object
            mock_span = MockSpan(OPENAI_CHAT_COMPLETION)
            
            # Process the mock span with the actual AgentsDetailedExporter from the instrumentor
            process_with_instrumentor(mock_span, AgentsDetailedExporter, captured_attributes)
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes.items():
                span.set_attribute(key, val)

        # Get all spans and log them for debugging
        spans = instrumentation.get_finished_spans()
        logger.info(f"Instrumentation Tester: Found {len(spans)} finished spans")
        for i, s in enumerate(spans):
            logger.info(f"Span {i}: name={s.name}, attributes={s.attributes}")
            
        # Examine the first span generated from the instrumentor
        instrumented_span = spans[0]
        logger.info(f"Validating span: {instrumented_span.name}")
        
        # Check all required attributes from our reference model against the actual span
        for key, expected_value in EXPECTED_CHAT_COMPLETION_SPAN_ATTRIBUTES.items():
            # Skip library version which might change
            if key == "library.version":
                continue
                
            # Assert the attribute exists 
            assert key in instrumented_span.attributes, f"Missing expected attribute '{key}'"
            
            # Assert it has the expected value
            actual_value = instrumented_span.attributes[key]
            assert actual_value == expected_value, \
                f"Attribute '{key}' has wrong value. Expected: {expected_value}, Actual: {actual_value}"
                
        # Also verify we don't have any unexpected attributes related to completions
        # This helps catch duplicate or incorrect attribute names
        completion_prefix = "gen_ai.completion.0"
        completion_attrs = [k for k in instrumented_span.attributes.keys() if k.startswith(completion_prefix)]
        expected_completion_attrs = [k for k in EXPECTED_CHAT_COMPLETION_SPAN_ATTRIBUTES.keys() if k.startswith(completion_prefix)]
        
        # We should have exactly the expected attributes, nothing more
        assert set(completion_attrs) == set(expected_completion_attrs), \
            f"Unexpected completion attributes. Found: {completion_attrs}, Expected: {expected_completion_attrs}"

    def test_openai_completion_with_tool_calls(self, instrumentation):
        """Test serialization of OpenAI ChatCompletion with tool calls using the actual instrumentor"""
        # Dictionary to capture attributes from the instrumentor
        captured_attributes = {}
        
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span for our test
        with tracer.start_as_current_span("test_tool_calls_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "llm")
            
            # Create a mock span with the ChatCompletion object that has tool calls
            mock_span = MockSpan(OPENAI_CHAT_COMPLETION_WITH_TOOL_CALLS)
            
            # Process the mock span with the actual AgentsDetailedExporter from the instrumentor
            process_with_instrumentor(mock_span, AgentsDetailedExporter, captured_attributes)
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes.items():
                span.set_attribute(key, val)

        # Get all spans and log them for debugging
        spans = instrumentation.get_finished_spans()
        logger.info(f"Instrumentation Tester: Found {len(spans)} finished spans")
        for i, s in enumerate(spans):
            logger.info(f"Span {i}: name={s.name}, attributes={s.attributes}")
            
        # Examine the first span generated from the instrumentor
        instrumented_span = spans[0]
        logger.info(f"Validating span: {instrumented_span.name}")
        
        # Check all required attributes from our reference model against the actual span
        for key, expected_value in EXPECTED_TOOL_CALLS_SPAN_ATTRIBUTES.items():
            # Skip library version which might change
            if key == "library.version":
                continue
                
            # Assert the attribute exists 
            assert key in instrumented_span.attributes, f"Missing expected attribute '{key}'"
            
            # Assert it has the expected value
            actual_value = instrumented_span.attributes[key]
            assert actual_value == expected_value, \
                f"Attribute '{key}' has wrong value. Expected: {expected_value}, Actual: {actual_value}"

        # Also verify we don't have any unexpected attributes related to tool calls
        # This helps catch duplicate or incorrect attribute names
        tool_call_prefix = "gen_ai.completion.0.tool_calls"
        tool_call_attrs = [k for k in instrumented_span.attributes.keys() if k.startswith(tool_call_prefix)]
        expected_tool_call_attrs = [k for k in EXPECTED_TOOL_CALLS_SPAN_ATTRIBUTES.keys() if k.startswith(tool_call_prefix)]
        
        # We should have exactly the expected attributes, nothing more
        assert set(tool_call_attrs) == set(expected_tool_call_attrs), \
            f"Unexpected tool call attributes. Found: {tool_call_attrs}, Expected: {expected_tool_call_attrs}"

    def test_openai_completion_with_function_call(self, instrumentation):
        """Test serialization of OpenAI ChatCompletion with function call using the actual instrumentor"""
        # Dictionary to capture attributes from the instrumentor
        captured_attributes = {}
        
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span for our test
        with tracer.start_as_current_span("test_function_call_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "llm")
            
            # Create a mock span with the ChatCompletion object that has a function call
            mock_span = MockSpan(OPENAI_CHAT_COMPLETION_WITH_FUNCTION_CALL)
            
            # Process the mock span with the actual AgentsDetailedExporter from the instrumentor
            process_with_instrumentor(mock_span, AgentsDetailedExporter, captured_attributes)
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes.items():
                span.set_attribute(key, val)

        # Get all spans and log them for debugging
        spans = instrumentation.get_finished_spans()
        logger.info(f"Instrumentation Tester: Found {len(spans)} finished spans")
        for i, s in enumerate(spans):
            logger.info(f"Span {i}: name={s.name}, attributes={s.attributes}")
            
        # Examine the first span generated from the instrumentor
        instrumented_span = spans[0]
        logger.info(f"Validating span: {instrumented_span.name}")
        
        # Check all required attributes from our reference model against the actual span
        for key, expected_value in EXPECTED_FUNCTION_CALL_SPAN_ATTRIBUTES.items():
            # Skip library version which might change
            if key == "library.version":
                continue
                
            # Assert the attribute exists 
            assert key in instrumented_span.attributes, f"Missing expected attribute '{key}'"
            
            # Assert it has the expected value
            actual_value = instrumented_span.attributes[key]
            assert actual_value == expected_value, \
                f"Attribute '{key}' has wrong value. Expected: {expected_value}, Actual: {actual_value}"

        # Also verify we don't have any unexpected attributes related to function calls
        # This helps catch duplicate or incorrect attribute names
        function_call_prefix = "gen_ai.completion.0.function_call"
        function_call_attrs = [k for k in instrumented_span.attributes.keys() if k.startswith(function_call_prefix)]
        expected_function_call_attrs = [k for k in EXPECTED_FUNCTION_CALL_SPAN_ATTRIBUTES.keys() if k.startswith(function_call_prefix)]
        
        # We should have exactly the expected attributes, nothing more
        assert set(function_call_attrs) == set(expected_function_call_attrs), \
            f"Unexpected function call attributes. Found: {function_call_attrs}, Expected: {expected_function_call_attrs}"