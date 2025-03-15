"""Tests for the model response serialization functionality"""

import json
from typing import Any, Dict, List, Optional, Union

import pytest
from opentelemetry import trace
from opentelemetry.trace import StatusCode

# Import actual OpenAI response types
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

# Keep the dictionary version for comparison with direct dictionary handling
MODEL_RESPONSE_DICT = {
    "id": "chatcmpl-123",
    "model": "gpt-4-0125-preview",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "This is a test response."
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 8,
        "total_tokens": 18
    },
    "system_fingerprint": "fp_44f3",
    "object": "chat.completion",
    "created": 1677858242
}


class TestModelResponseSerialization:
    """Tests for model response serialization in spans"""

    @pytest.fixture
    def instrumentation(self):
        """Set up instrumentation for tests"""
        return InstrumentationTester()

    def test_dict_response_serialization(self, instrumentation):
        """Test serialization of dictionary response"""
        # Set up
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span and add response as output
        with tracer.start_as_current_span("test_response_span") as span:
            # Set the span type and model output
            span.set_attribute("span.kind", "llm")
            span.set_attribute("test_output", json.dumps(MODEL_RESPONSE_DICT))
            
            # Import model_as_dict directly from the Agents SDK
            from third_party.opentelemetry.instrumentation.agents.agentops_agents_instrumentor import model_as_dict
            
            # Create a mock span data object similar to what would be captured
            class MockSpanData:
                def __init__(self, output):
                    self.output = output
            
            # Create span data with the model response
            span_data = MockSpanData(MODEL_RESPONSE_DICT)
            
            # Extract attributes
            attributes = {}
            if hasattr(span_data, "output") and span_data.output:
                output = span_data.output
                
                # Convert to dict using model_as_dict
                output_dict = model_as_dict(output)
                
                if output_dict:
                    # Extract model
                    if "model" in output_dict:
                        attributes[SpanAttributes.LLM_RESPONSE_MODEL] = output_dict["model"]
                    
                    # Extract ID
                    if "id" in output_dict:
                        attributes[SpanAttributes.LLM_RESPONSE_ID] = output_dict["id"]
                    
                    # Extract system fingerprint
                    if "system_fingerprint" in output_dict:
                        attributes[SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT] = output_dict["system_fingerprint"]
                    
                    # Handle usage metrics
                    if "usage" in output_dict and output_dict["usage"]:
                        usage = output_dict["usage"]
                        if isinstance(usage, dict):
                            if "total_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]
                            if "completion_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["completion_tokens"]
                            if "prompt_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["prompt_tokens"]
            
            # Set attributes on the span
            for key, val in attributes.items():
                span.set_attribute(key, val)

        # Get all spans
        spans = instrumentation.get_finished_spans()
        assert len(spans) > 0
        
        # Get the test span
        test_span = spans[0]
        
        # Verify the response attributes were properly serialized
        assert test_span.attributes.get(SpanAttributes.LLM_RESPONSE_MODEL) == MODEL_RESPONSE_DICT["model"]
        assert test_span.attributes.get(SpanAttributes.LLM_RESPONSE_ID) == MODEL_RESPONSE_DICT["id"]
        assert test_span.attributes.get(SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT) == MODEL_RESPONSE_DICT["system_fingerprint"]
        assert test_span.attributes.get(SpanAttributes.LLM_USAGE_TOTAL_TOKENS) == MODEL_RESPONSE_DICT["usage"]["total_tokens"]
        assert test_span.attributes.get(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS) == MODEL_RESPONSE_DICT["usage"]["completion_tokens"]
        assert test_span.attributes.get(SpanAttributes.LLM_USAGE_PROMPT_TOKENS) == MODEL_RESPONSE_DICT["usage"]["prompt_tokens"]

    def test_openai_chat_completion_serialization(self, instrumentation):
        """Test serialization of actual OpenAI ChatCompletion response"""
        # Set up
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span and add response as output
        with tracer.start_as_current_span("test_openai_response_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "llm")
            
            # Use the model_as_dict functionality from Agents SDK
            from third_party.opentelemetry.instrumentation.agents.agentops_agents_instrumentor import model_as_dict
            
            # Create a mock span data object
            class MockSpanData:
                def __init__(self, output):
                    self.output = output
            
            # Create span data with the model response
            span_data = MockSpanData(OPENAI_CHAT_COMPLETION)
            
            # Extract attributes using the same logic as in the Agent SDK
            attributes = {}
            if hasattr(span_data, "output") and span_data.output:
                output = span_data.output
                
                # Convert to dict using model_as_dict
                output_dict = model_as_dict(output)
                
                if output_dict:
                    # Extract model
                    if "model" in output_dict:
                        attributes[SpanAttributes.LLM_RESPONSE_MODEL] = output_dict["model"]
                    
                    # Extract ID
                    if "id" in output_dict:
                        attributes[SpanAttributes.LLM_RESPONSE_ID] = output_dict["id"]
                    
                    # Extract system fingerprint
                    if "system_fingerprint" in output_dict:
                        attributes[SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT] = output_dict["system_fingerprint"]
                    
                    # Handle usage metrics
                    if "usage" in output_dict and output_dict["usage"]:
                        usage = output_dict["usage"]
                        if isinstance(usage, dict):
                            if "total_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]
                            if "completion_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["completion_tokens"]
                            if "prompt_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["prompt_tokens"]
            
            # Set attributes on the span
            for key, val in attributes.items():
                span.set_attribute(key, val)

        # Get all spans
        spans = instrumentation.get_finished_spans()
        assert len(spans) > 0
        
        # Get the test span
        test_span = spans[0]
        
        # Verify the response attributes were properly serialized
        assert test_span.attributes.get(SpanAttributes.LLM_RESPONSE_MODEL) == OPENAI_CHAT_COMPLETION.model
        assert test_span.attributes.get(SpanAttributes.LLM_RESPONSE_ID) == OPENAI_CHAT_COMPLETION.id
        assert test_span.attributes.get(SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT) == OPENAI_CHAT_COMPLETION.system_fingerprint
        assert test_span.attributes.get(SpanAttributes.LLM_USAGE_TOTAL_TOKENS) == OPENAI_CHAT_COMPLETION.usage.total_tokens
        assert test_span.attributes.get(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS) == OPENAI_CHAT_COMPLETION.usage.completion_tokens
        assert test_span.attributes.get(SpanAttributes.LLM_USAGE_PROMPT_TOKENS) == OPENAI_CHAT_COMPLETION.usage.prompt_tokens

    def test_openai_response_with_tool_calls(self, instrumentation):
        """Test serialization of OpenAI response with tool calls"""
        # Set up
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span and add response as output
        with tracer.start_as_current_span("test_tool_calls_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "llm")
            
            # Use the model_as_dict functionality from Agents SDK
            from third_party.opentelemetry.instrumentation.agents.agentops_agents_instrumentor import model_as_dict
            
            # Create a mock span data object
            class MockSpanData:
                def __init__(self, output):
                    self.output = output
            
            # Create span data with the model response
            span_data = MockSpanData(OPENAI_CHAT_COMPLETION_WITH_TOOL_CALLS)
            
            # Extract attributes using similar logic to the Agent SDK
            attributes = {}
            if hasattr(span_data, "output") and span_data.output:
                output = span_data.output
                
                # Convert to dict using model_as_dict
                output_dict = model_as_dict(output)
                
                if output_dict:
                    # Extract model
                    if "model" in output_dict:
                        attributes[SpanAttributes.LLM_RESPONSE_MODEL] = output_dict["model"]
                    
                    # Extract ID and system fingerprint
                    if "id" in output_dict:
                        attributes[SpanAttributes.LLM_RESPONSE_ID] = output_dict["id"]
                    if "system_fingerprint" in output_dict:
                        attributes[SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT] = output_dict["system_fingerprint"]
                    
                    # Handle usage metrics
                    if "usage" in output_dict and output_dict["usage"]:
                        usage = output_dict["usage"]
                        if isinstance(usage, dict):
                            if "total_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]
                            if "completion_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["completion_tokens"]
                            if "prompt_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["prompt_tokens"]
                    
                    # Handle completions - extract specific fields from choices
                    if "choices" in output_dict and output_dict["choices"]:
                        for choice in output_dict["choices"]:
                            index = choice.get("index", 0)
                            prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{index}"
                            
                            # Extract finish reason
                            if "finish_reason" in choice:
                                attributes[f"{prefix}.finish_reason"] = choice["finish_reason"]
                            
                            # Extract message content
                            message = choice.get("message", {})
                            if message:
                                if "role" in message:
                                    attributes[f"{prefix}.role"] = message["role"]
                                if "content" in message and message["content"]:
                                    attributes[f"{prefix}.content"] = message["content"]
                                
                                # Handle tool calls if present
                                if "tool_calls" in message:
                                    for i, tool_call in enumerate(message["tool_calls"]):
                                        if "function" in tool_call:
                                            function = tool_call["function"]
                                            attributes[f"{prefix}.tool_calls.{i}.id"] = tool_call.get("id")
                                            attributes[f"{prefix}.tool_calls.{i}.name"] = function.get("name")
                                            attributes[f"{prefix}.tool_calls.{i}.arguments"] = function.get("arguments")
            
            # Set attributes on the span
            for key, val in attributes.items():
                span.set_attribute(key, val)

        # Get all spans
        spans = instrumentation.get_finished_spans()
        assert len(spans) > 0
        
        # Get the test span
        test_span = spans[0]
        
        # Verify the response attributes were properly serialized
        assert test_span.attributes.get(SpanAttributes.LLM_RESPONSE_MODEL) == OPENAI_CHAT_COMPLETION_WITH_TOOL_CALLS.model
        assert test_span.attributes.get(SpanAttributes.LLM_RESPONSE_ID) == OPENAI_CHAT_COMPLETION_WITH_TOOL_CALLS.id
        assert test_span.attributes.get(SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT) == OPENAI_CHAT_COMPLETION_WITH_TOOL_CALLS.system_fingerprint
        
        # Verify tool calls are properly serialized
        choice_idx = 0  # First choice
        tool_call_idx = 0  # First tool call
        tool_call = OPENAI_CHAT_COMPLETION_WITH_TOOL_CALLS.choices[0].message.tool_calls[0]
        
        prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{choice_idx}"
        assert test_span.attributes.get(f"{prefix}.finish_reason") == "tool_calls"
        assert test_span.attributes.get(f"{prefix}.role") == "assistant"
        assert test_span.attributes.get(f"{prefix}.tool_calls.{tool_call_idx}.id") == tool_call.id
        assert test_span.attributes.get(f"{prefix}.tool_calls.{tool_call_idx}.name") == tool_call.function.name
        assert test_span.attributes.get(f"{prefix}.tool_calls.{tool_call_idx}.arguments") == tool_call.function.arguments

    def test_openai_response_with_function_call(self, instrumentation):
        """Test serialization of OpenAI response with function call"""
        # Set up
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span and add response as output
        with tracer.start_as_current_span("test_function_call_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "llm")
            
            # Use the model_as_dict functionality from Agents SDK
            from third_party.opentelemetry.instrumentation.agents.agentops_agents_instrumentor import model_as_dict
            
            # Create a mock span data object
            class MockSpanData:
                def __init__(self, output):
                    self.output = output
            
            # Create span data with the model response
            span_data = MockSpanData(OPENAI_CHAT_COMPLETION_WITH_FUNCTION_CALL)
            
            # Extract attributes
            attributes = {}
            if hasattr(span_data, "output") and span_data.output:
                output = span_data.output
                
                # Convert to dict using model_as_dict
                output_dict = model_as_dict(output)
                
                if output_dict:
                    # Extract model
                    if "model" in output_dict:
                        attributes[SpanAttributes.LLM_RESPONSE_MODEL] = output_dict["model"]
                    
                    # Extract ID
                    if "id" in output_dict:
                        attributes[SpanAttributes.LLM_RESPONSE_ID] = output_dict["id"]
                    
                    # Handle usage metrics
                    if "usage" in output_dict and output_dict["usage"]:
                        usage = output_dict["usage"]
                        if isinstance(usage, dict):
                            if "total_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]
                            if "completion_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["completion_tokens"]
                            if "prompt_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["prompt_tokens"]
                    
                    # Handle completions - extract specific fields from choices
                    if "choices" in output_dict and output_dict["choices"]:
                        for choice in output_dict["choices"]:
                            index = choice.get("index", 0)
                            prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{index}"
                            
                            # Extract finish reason
                            if "finish_reason" in choice:
                                attributes[f"{prefix}.finish_reason"] = choice["finish_reason"]
                            
                            # Extract message content
                            message = choice.get("message", {})
                            if message:
                                if "role" in message:
                                    attributes[f"{prefix}.role"] = message["role"]
                                if "content" in message and message["content"]:
                                    attributes[f"{prefix}.content"] = message["content"]
                                
                                # Handle function calls if present
                                if "function_call" in message:
                                    function_call = message["function_call"]
                                    attributes[f"{prefix}.function_call.name"] = function_call.get("name")
                                    attributes[f"{prefix}.function_call.arguments"] = function_call.get("arguments")
            
            # Set attributes on the span
            for key, val in attributes.items():
                span.set_attribute(key, val)

        # Get all spans
        spans = instrumentation.get_finished_spans()
        assert len(spans) > 0
        
        # Get the test span
        test_span = spans[0]
        
        # Verify the response attributes were properly serialized
        assert test_span.attributes.get(SpanAttributes.LLM_RESPONSE_MODEL) == OPENAI_CHAT_COMPLETION_WITH_FUNCTION_CALL.model
        assert test_span.attributes.get(SpanAttributes.LLM_RESPONSE_ID) == OPENAI_CHAT_COMPLETION_WITH_FUNCTION_CALL.id
        
        # Verify function call is properly serialized
        choice_idx = 0  # First choice
        function_call = OPENAI_CHAT_COMPLETION_WITH_FUNCTION_CALL.choices[0].message.function_call
        
        prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{choice_idx}"
        assert test_span.attributes.get(f"{prefix}.finish_reason") == "function_call"
        assert test_span.attributes.get(f"{prefix}.role") == "assistant"
        assert test_span.attributes.get(f"{prefix}.function_call.name") == function_call.name
        assert test_span.attributes.get(f"{prefix}.function_call.arguments") == function_call.arguments