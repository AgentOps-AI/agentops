"""
these tests relate specifically to the responses type from the open AI API, 
not to be confused with the completion type from the open AIAPI
"""

import json
from typing import Any, Dict, List, Optional, Union

import pytest
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from openai.types.responses import (
    Response,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseUsage,
)
from openai.types.responses.response_usage import OutputTokensDetails

import agentops
from agentops.sdk.core import TracingCore
from agentops.semconv import SpanAttributes
from tests.unit.sdk.instrumentation_tester import InstrumentationTester


# New OpenAI Response API object
OPENAI_RESPONSE = Response(
    id="resp_123abc",
    created_at=1677858245,
    model="gpt-4o",
    object="response",
    output=[
        ResponseOutputMessage(
            id="msg_abc123",
            type="message",
            content=[
                ResponseOutputText(
                    type="output_text",
                    text="This is a test response from the new Responses API.",
                    annotations=[]
                )
            ],
            role="assistant",
            status="completed"
        )
    ],
    usage=ResponseUsage(
        input_tokens=10,
        output_tokens=8,
        total_tokens=18,
        output_tokens_details=OutputTokensDetails(
            reasoning_tokens=2
        )
    ),
    parallel_tool_calls=False,
    status="completed",
    tools=[],
    tool_choice="none"
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
        
    def test_openai_response_serialization(self, instrumentation):
        """Test serialization of OpenAI Response API object"""
        # Set up
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span and add response as output
        with tracer.start_as_current_span("test_openai_response_api_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "llm")
            
            # Use the model_as_dict functionality from Agents SDK
            from third_party.opentelemetry.instrumentation.agents.agentops_agents_instrumentor import model_as_dict
            
            # Create a mock span data object
            class MockSpanData:
                def __init__(self, output):
                    self.output = output
            
            # Create span data with the model response
            span_data = MockSpanData(OPENAI_RESPONSE)
            
            # Extract attributes using the same logic as in the Agent SDK
            attributes = {}
            if hasattr(span_data, "output") and span_data.output:
                output = span_data.output
                
                # Convert to dict using model_as_dict
                output_dict = model_as_dict(output)
                
                # Log the output dict to understand its structure
                print(f"Output dict: {output_dict}")
                
                if output_dict:
                    # Extract model
                    if "model" in output_dict:
                        attributes[SpanAttributes.LLM_RESPONSE_MODEL] = output_dict["model"]
                    
                    # Extract ID
                    if "id" in output_dict:
                        attributes[SpanAttributes.LLM_RESPONSE_ID] = output_dict["id"]
                    
                    # Handle usage metrics with different naming for Responses API
                    if "usage" in output_dict and output_dict["usage"]:
                        usage = output_dict["usage"]
                        if isinstance(usage, dict):
                            if "total_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]
                            
                            if "input_tokens" in usage:
                                # Handle Responses API format
                                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["input_tokens"]
                                
                            if "output_tokens" in usage:
                                # Handle Responses API format
                                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["output_tokens"]
                                
                            # Original chat completion format    
                            if "completion_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["completion_tokens"]
                            if "prompt_tokens" in usage:
                                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["prompt_tokens"]
                    
                    # Extract output text from responses API format
                    if "output" in output_dict and isinstance(output_dict["output"], list):
                        for idx, item in enumerate(output_dict["output"]):
                            if isinstance(item, dict):
                                if item.get("type") == "message" and "content" in item:
                                    for content_idx, content in enumerate(item.get("content", [])):
                                        if isinstance(content, dict) and content.get("type") == "output_text":
                                            prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{idx}"
                                            attributes[f"{prefix}.content"] = content.get("text", "")
                                            attributes[f"{prefix}.role"] = item.get("role", "assistant")
            
            # Set attributes on the span
            for key, val in attributes.items():
                span.set_attribute(key, val)

        # Get all spans
        spans = instrumentation.get_finished_spans()
        assert len(spans) > 0
        
        # Get the test span
        test_span = spans[0]
        print(f"Span 0: name=test_openai_response_api_span, attributes={test_span.attributes}")
        
        # Verify the response attributes were properly serialized
        assert test_span.attributes.get(SpanAttributes.LLM_RESPONSE_MODEL) == OPENAI_RESPONSE.model
        assert test_span.attributes.get(SpanAttributes.LLM_RESPONSE_ID) == OPENAI_RESPONSE.id
        assert test_span.attributes.get(SpanAttributes.LLM_USAGE_TOTAL_TOKENS) == 18

