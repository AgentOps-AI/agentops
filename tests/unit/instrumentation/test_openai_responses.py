"""
Tests for OpenAI Response API Serialization

This module contains tests for properly handling and serializing the new OpenAI Response API format.

Important distinction:
- OpenAI Response API: Used exclusively by the OpenAI Agents SDK, these objects use 
  the "Response" class with an "output" array containing messages and their content.
  
- OpenAI Chat Completion API: The traditional OpenAI API format that uses the "ChatCompletion" 
  class with a "choices" array containing messages.

This separation ensures we correctly implement attribute extraction for both formats
in our instrumentation.
"""

import json
from typing import Any, Dict, List, Optional, Union

import pytest
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from agentops.logging import logger

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
from third_party.opentelemetry.instrumentation.agents.agentops_agents_instrumentor import AgentsDetailedExporter
from tests.unit.instrumentation.mock_span import MockSpan, process_with_instrumentor


# Test fixture: A representative OpenAI Response API object
# 
# This is a complete instance of the Response class from the OpenAI Agents SDK.
# It demonstrates the structure we need to handle in our instrumentation:
# - Has an "output" array (instead of "choices")
# - Content is nested in a specific structure: output→message→content→text item
# - Uses input_tokens/output_tokens instead of prompt_tokens/completion_tokens
# - Includes special details like output_tokens_details.reasoning_tokens
#
# Our instrumentation must correctly extract all relevant fields from this structure
# and map them to the appropriate span attributes.
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

# We don't need the Chat Completion example here - this test focuses only on the Response API

# Test reference: Expected span attributes from processing a Response API object
#
# This dictionary defines precisely what span attributes we expect our instrumentor
# to produce when processing an OpenAI Response API object (like OPENAI_RESPONSE above).
# 
# The goal of our test is to ensure that when our instrumentation processes a Response API 
# object, it correctly extracts and maps all these attributes with the correct values.
#
# Key aspects we're testing:
# 1. Correct extraction of metadata (model, id)
# 2. Proper mapping of token usage (input→prompt, output→completion) 
# 3. Extraction of special fields like reasoning_tokens
# 4. Most importantly: proper extraction of content from the nested output structure
#
# This serves as our "source of truth" for verification in the test.
EXPECTED_RESPONSE_SPAN_ATTRIBUTES = {
    # Basic response metadata - using proper semantic conventions
    SpanAttributes.LLM_RESPONSE_MODEL: "gpt-4o",
    SpanAttributes.LLM_RESPONSE_ID: "resp_123abc",
    
    # Token usage metrics - using proper semantic conventions
    # Note input_tokens/output_tokens from Responses API get mapped to prompt/completion
    SpanAttributes.LLM_USAGE_TOTAL_TOKENS: 18,
    SpanAttributes.LLM_USAGE_PROMPT_TOKENS: 10,
    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: 8,
    f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.reasoning": 2,  # Special field from output_tokens_details
    
    # Content extraction from Response API format - using proper semantic conventions
    f"{SpanAttributes.LLM_COMPLETIONS}.0.content": "This is a test response from the new Responses API.",
    f"{SpanAttributes.LLM_COMPLETIONS}.0.role": "assistant",
    
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
        
    def test_openai_response_serialization(self, instrumentation):
        """Test serialization of OpenAI Response API object using the actual instrumentor"""
        # Dictionary to capture attributes from the instrumentor
        captured_attributes = {}
        
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span for our test
        with tracer.start_as_current_span("test_openai_response_api_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "llm")
            
            # Create a mock span with the Response API object
            mock_span = MockSpan(OPENAI_RESPONSE)
            
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
        for key, expected_value in EXPECTED_RESPONSE_SPAN_ATTRIBUTES.items():
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
        expected_completion_attrs = [k for k in EXPECTED_RESPONSE_SPAN_ATTRIBUTES.keys() if k.startswith(completion_prefix)]
        
        # We should have exactly the expected attributes, nothing more
        assert set(completion_attrs) == set(expected_completion_attrs), \
            f"Unexpected completion attributes. Found: {completion_attrs}, Expected: {expected_completion_attrs}"

