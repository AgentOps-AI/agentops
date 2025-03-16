"""
Tests for OpenAI Agents SDK Instrumentation

This module contains tests for properly handling and serializing data from the OpenAI Agents SDK.
It verifies that our instrumentation correctly captures and instruments agent runs, tool usage,
and other operations specific to the OpenAI Agents SDK.

NOTE: All tests must define expected_attributes dictionaries to validate response data in spans.
This helps ensure consistent attribute structure for downstream OpenTelemetry consumers.

The Agents SDK has its own unique structure with:
- Agent runs with specific attributes and properties
- Tool calls and agent handoffs
- Raw responses that may contain either ChatCompletion or Response API objects
"""

import json
import os
import time
from typing import Any, Dict, List, Optional, Union
import inspect
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
from opentelemetry import trace
from opentelemetry.trace import StatusCode

# Load real OpenAI responses from fixtures
def load_fixture(fixture_name):
    """Load a fixture file from the fixtures directory."""
    fixture_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "fixtures",
        fixture_name
    )
    try:
        with open(fixture_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        pytest.skip(f"Fixture {fixture_name} not found. Run the export_response.py script first.")

# Load the real response data from fixtures
REAL_OPENAI_RESPONSE = load_fixture("openai_response.json")
REAL_OPENAI_TOOL_CALLS_RESPONSE = load_fixture("openai_response_tool_calls.json")
OPENAI_CHAT_COMPLETION = load_fixture("openai_chat_completion.json")
OPENAI_CHAT_TOOL_CALLS = load_fixture("openai_chat_tool_calls.json")

# Import necessary libraries for testing
import agentops
from agentops.sdk.core import TracingCore
from agentops.semconv import (
    SpanAttributes, 
    AgentAttributes, 
    WorkflowAttributes, 
    CoreAttributes,
    InstrumentationAttributes,
    MessageAttributes
)
from tests.unit.sdk.instrumentation_tester import InstrumentationTester
from agentops.instrumentation.openai_agents.exporter import OpenAIAgentsExporter, get_model_info
# These are in separate modules, import directly from those
from agentops.instrumentation.openai_agents.processor import OpenAIAgentsProcessor
from agentops.instrumentation.openai_agents.instrumentor import OpenAIAgentsInstrumentor
from agentops.instrumentation.openai_agents import LIBRARY_NAME, LIBRARY_VERSION
from tests.unit.instrumentation.mock_span import MockSpan, MockTracer, process_with_instrumentor

# Use the correct imports
from agents import (
    Agent, 
    add_trace_processor,
    ModelSettings,
    Runner, 
    RunConfig,
    Tool,
    GenerationSpanData, 
    AgentSpanData, 
    FunctionSpanData
)
from openai.types.responses import Response


class TestAgentsSdkInstrumentation:
    """Tests for OpenAI Agents SDK instrumentation using real fixtures"""

    @pytest.fixture
    def instrumentation(self):
        """Set up instrumentation for tests"""
        return InstrumentationTester()
    
    def test_response_api_span_serialization(self, instrumentation):
        """Test serialization of Generation spans from Agents SDK using Response API with real fixture data"""
        # Dictionary to capture attributes from the instrumentor
        captured_attributes = {}
        
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span for our test
        with tracer.start_as_current_span("test_response_api_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "client")
            
            # Create mock data structure that matches what the instrumentor expects
            # but uses the real fixture data for the output field
            span_data = {
                "model": REAL_OPENAI_RESPONSE["model"],
                "model_config": {
                    "temperature": REAL_OPENAI_RESPONSE["temperature"],
                    "top_p": REAL_OPENAI_RESPONSE["top_p"]
                },
                "input": "What is the capital of France?",
                "output": REAL_OPENAI_RESPONSE,
                "usage": REAL_OPENAI_RESPONSE["usage"]
            }
            
            # Create the mock span with our prepared data
            mock_span = MockSpan(span_data, span_type="GenerationSpanData")
            
            # Process the mock span with the actual OpenAIAgentsExporter
            process_with_instrumentor(mock_span, OpenAIAgentsExporter, captured_attributes)
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes.items():
                span.set_attribute(key, val)

        # Get all spans
        spans = instrumentation.get_finished_spans()
            
        # Examine the first span generated from the instrumentor
        instrumented_span = spans[0]
        
        # Expected attribute values based on the fixture data using proper semantic conventions
        expected_attributes = {
            # Model metadata using semantic conventions
            SpanAttributes.LLM_REQUEST_MODEL: REAL_OPENAI_RESPONSE["model"],
            SpanAttributes.LLM_SYSTEM: "openai",
            SpanAttributes.LLM_REQUEST_TEMPERATURE: REAL_OPENAI_RESPONSE["temperature"],
            SpanAttributes.LLM_REQUEST_TOP_P: REAL_OPENAI_RESPONSE["top_p"],
            
            # Response metadata using semantic conventions
            SpanAttributes.LLM_RESPONSE_MODEL: REAL_OPENAI_RESPONSE["model"],
            SpanAttributes.LLM_RESPONSE_ID: REAL_OPENAI_RESPONSE["id"],
            
            # Token usage with proper semantic conventions
            SpanAttributes.LLM_USAGE_TOTAL_TOKENS: REAL_OPENAI_RESPONSE["usage"]["total_tokens"],
            SpanAttributes.LLM_USAGE_PROMPT_TOKENS: REAL_OPENAI_RESPONSE["usage"]["input_tokens"],
            SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: REAL_OPENAI_RESPONSE["usage"]["output_tokens"],
            f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.reasoning": REAL_OPENAI_RESPONSE["usage"]["output_tokens_details"]["reasoning_tokens"],
            
            # Content extraction with proper message semantic conventions
            MessageAttributes.COMPLETION_CONTENT.format(i=0): REAL_OPENAI_RESPONSE["output"][0]["content"][0]["text"],
            MessageAttributes.COMPLETION_ROLE.format(i=0): REAL_OPENAI_RESPONSE["output"][0]["role"],
        }
        
        # Check all required attributes from our reference model against the actual span
        for key, expected_value in expected_attributes.items():
            # Assert the attribute exists 
            assert key in instrumented_span.attributes, f"Missing expected attribute '{key}'"
            
            # Assert it has the expected value
            actual_value = instrumented_span.attributes[key]
            assert actual_value == expected_value, \
                f"Attribute '{key}' has wrong value. Expected: {expected_value}, Actual: {actual_value}"
        
        # Per the semantic conventions, we do not set the root completion attribute
        # Instead, verify the message-specific content attribute is set correctly
        expected_text = REAL_OPENAI_RESPONSE["output"][0]["content"][0]["text"]
        content_attr = MessageAttributes.COMPLETION_CONTENT.format(i=0)
        assert content_attr in instrumented_span.attributes, f"Missing content attribute: {content_attr}"
        assert instrumented_span.attributes[content_attr] == expected_text, \
            f"Content attribute has incorrect value. Expected: '{expected_text}', got: '{instrumented_span.attributes[content_attr]}'"
                
        # Verify message attributes using the message semantic conventions
        message_prefix = "gen_ai.completion"
        message_attrs = [k for k in instrumented_span.attributes.keys() if k.startswith(message_prefix)]
        
        # Make sure we have the expected message attributes
        assert len(message_attrs) > 0, "No message attributes found with prefix 'gen_ai.completion'"
        
        # Check key message attributes are present
        assert MessageAttributes.COMPLETION_CONTENT.format(i=0) in message_attrs, "Missing completion content attribute"
        assert MessageAttributes.COMPLETION_ROLE.format(i=0) in message_attrs, "Missing completion role attribute"
            
        # Verify token mapping and special fields
        assert SpanAttributes.LLM_USAGE_PROMPT_TOKENS in instrumented_span.attributes, f"Missing {SpanAttributes.LLM_USAGE_PROMPT_TOKENS} attribute"
        assert instrumented_span.attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == REAL_OPENAI_RESPONSE["usage"]["input_tokens"], "Incorrect prompt_tokens value"
        
        assert SpanAttributes.LLM_USAGE_COMPLETION_TOKENS in instrumented_span.attributes, f"Missing {SpanAttributes.LLM_USAGE_COMPLETION_TOKENS} attribute"
        assert instrumented_span.attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == REAL_OPENAI_RESPONSE["usage"]["output_tokens"], "Incorrect completion_tokens value"
        
        reasoning_attr = f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.reasoning"
        assert reasoning_attr in instrumented_span.attributes, f"Missing {reasoning_attr} attribute"
        assert instrumented_span.attributes[reasoning_attr] == REAL_OPENAI_RESPONSE["usage"]["output_tokens_details"]["reasoning_tokens"], "Incorrect reasoning_tokens value"
        
    def test_tool_calls_span_serialization(self, instrumentation):
        """Test serialization of Generation spans with tool calls from Agents SDK using real fixture data"""
        # Dictionary to capture attributes from the instrumentor
        captured_attributes = {}
        
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span for our test
        with tracer.start_as_current_span("test_tool_calls_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "client")
            
            # Create mock data structure that matches what the instrumentor expects
            # but uses the real fixture data for the output field
            span_data = {
                "model": REAL_OPENAI_TOOL_CALLS_RESPONSE["model"],
                "model_config": {
                    "temperature": REAL_OPENAI_TOOL_CALLS_RESPONSE["temperature"],
                    "top_p": REAL_OPENAI_TOOL_CALLS_RESPONSE["top_p"]
                },
                "input": "What's the weather in San Francisco?",
                "output": REAL_OPENAI_TOOL_CALLS_RESPONSE,
                "usage": REAL_OPENAI_TOOL_CALLS_RESPONSE["usage"]
            }
            
            # Create a mock span with our prepared data
            mock_span = MockSpan(span_data, span_type="GenerationSpanData")
            
            # Process the mock span with the actual OpenAIAgentsExporter
            process_with_instrumentor(mock_span, OpenAIAgentsExporter, captured_attributes)
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes.items():
                span.set_attribute(key, val)

        # Get all spans
        spans = instrumentation.get_finished_spans()
            
        # Examine the first span generated from the instrumentor
        instrumented_span = spans[0]
        
        # Extract tool call details for verification
        tool_call = REAL_OPENAI_TOOL_CALLS_RESPONSE["output"][0]
        
        # Expected attribute values based on the fixture data using proper semantic conventions
        expected_attributes = {
            # Model metadata using semantic conventions
            SpanAttributes.LLM_REQUEST_MODEL: REAL_OPENAI_TOOL_CALLS_RESPONSE["model"],
            SpanAttributes.LLM_SYSTEM: "openai",
            SpanAttributes.LLM_REQUEST_TEMPERATURE: REAL_OPENAI_TOOL_CALLS_RESPONSE["temperature"],
            SpanAttributes.LLM_REQUEST_TOP_P: REAL_OPENAI_TOOL_CALLS_RESPONSE["top_p"],
            
            # Response metadata using semantic conventions
            SpanAttributes.LLM_RESPONSE_MODEL: REAL_OPENAI_TOOL_CALLS_RESPONSE["model"],
            SpanAttributes.LLM_RESPONSE_ID: REAL_OPENAI_TOOL_CALLS_RESPONSE["id"],
            
            # Token usage with proper semantic conventions
            SpanAttributes.LLM_USAGE_TOTAL_TOKENS: REAL_OPENAI_TOOL_CALLS_RESPONSE["usage"]["total_tokens"],
            SpanAttributes.LLM_USAGE_PROMPT_TOKENS: REAL_OPENAI_TOOL_CALLS_RESPONSE["usage"]["input_tokens"],
            SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: REAL_OPENAI_TOOL_CALLS_RESPONSE["usage"]["output_tokens"],
            
            # Tool call details with proper message semantic conventions
            MessageAttributes.TOOL_CALL_ID.format(i=0, j=0): tool_call["id"],
            MessageAttributes.TOOL_CALL_NAME.format(i=0, j=0): tool_call["name"],
            MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0, j=0): tool_call["arguments"]
        }
        
        # Check all required attributes from our reference model against the actual span
        for key, expected_value in expected_attributes.items():
            # Assert the attribute exists 
            assert key in instrumented_span.attributes, f"Missing expected attribute '{key}'"
            
            # Assert it has the expected value
            actual_value = instrumented_span.attributes[key]
            assert actual_value == expected_value, \
                f"Attribute '{key}' has wrong value. Expected: {expected_value}, Actual: {actual_value}"
        
        # Verify the tool calls attributes by checking for specific semantic convention attributes
        # We need to look for the three core tool call attributes from MessageAttributes
        
        # First, check that all three required tool call attributes exist
        tool_id_attr = MessageAttributes.TOOL_CALL_ID.format(i=0, j=0)
        tool_name_attr = MessageAttributes.TOOL_CALL_NAME.format(i=0, j=0)
        tool_args_attr = MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0, j=0)
        
        assert tool_id_attr in instrumented_span.attributes, f"Missing tool call ID attribute: {tool_id_attr}"
        assert tool_name_attr in instrumented_span.attributes, f"Missing tool call name attribute: {tool_name_attr}"
        assert tool_args_attr in instrumented_span.attributes, f"Missing tool call arguments attribute: {tool_args_attr}"
        
        # Verify specific tool call details using MessageAttributes for the correct paths
        assert instrumented_span.attributes[tool_id_attr] == tool_call["id"], "Incorrect tool call ID"
        assert instrumented_span.attributes[tool_name_attr] == tool_call["name"], "Incorrect tool call name"
        assert instrumented_span.attributes[tool_args_attr] == tool_call["arguments"], "Incorrect tool call arguments"
        assert "San Francisco" in instrumented_span.attributes[tool_args_attr], "Expected location not found in arguments"

    def test_full_agent_integration_with_real_types(self, instrumentation):
        """
        Test the full integration of the OpenAI Agents SDK with AgentOps.
        This test uses the real Agents SDK types and runs a simulated agent execution.
        This test has been enhanced to validate data we know is available but not properly
        reflected in the final output.
        """
        # Create objects with real SDK classes
        response = Response.model_validate(REAL_OPENAI_RESPONSE)
        
        # Create model settings
        model_settings = ModelSettings(temperature=0.7, top_p=1.0)
        
        # Create an agent with the model settings
        agent_name = "TestAgent"
        agent = Agent(name=agent_name, instructions="You are a helpful assistant.", model_settings=model_settings)
        
        # Create a run configuration
        run_config = RunConfig(workflow_name="test_workflow")
        
        # Set up captured data for the processor
        captured_spans = []
        captured_attributes = {}
        
        # Create a mock tracer provider
        tracer_provider = MagicMock()
        
        # Track timestamps for validation
        start_time = time.time()
        
        # Mock the _export_span method
        def mock_export_span(span):
            # Extract span data
            captured_spans.append(span)
            
            # Add timing info that should be available
            if not hasattr(span, 'start_time'):
                span.start_time = start_time
            if not hasattr(span, 'end_time'):
                span.end_time = time.time()
            
            # Process with actual exporter
            process_with_instrumentor(span, OpenAIAgentsExporter, captured_attributes)
        
        # Create a mock processor
        mock_processor = MagicMock()
        mock_processor.on_span_start = MagicMock()
        mock_processor.on_span_end = MagicMock()
        mock_processor.exporter = MagicMock()
        mock_processor.exporter._export_span = mock_export_span
        
        # Use the real processor but without patching the SDK
        processor = OpenAIAgentsProcessor()
        processor.exporter = OpenAIAgentsExporter(tracer_provider)
            
        # Create span data using the real SDK classes with enhanced metadata
        metadata = {"test_metadata_key": "test_value", "environment": "test"}
        
        # Create an event we want to track
        event_data = {"event_type": "llm_request", "timestamp": start_time}
        
        gen_span_data = GenerationSpanData(
            model=REAL_OPENAI_RESPONSE["model"],
            model_config=model_settings,
            input="What is the capital of France?",
            output=response,
            usage=REAL_OPENAI_RESPONSE["usage"]
        )
        
        # Add extra attributes that should be available
        gen_span_data.from_agent = agent_name
        gen_span_data.tools = ["web_search", "calculator"]
        gen_span_data.metadata = metadata
        gen_span_data.events = [event_data]
        gen_span_data.output_type = "text"
        gen_span_data.handoffs = []
        
        # Create a span with our prepared data
        span = MockSpan({"data": gen_span_data}, span_type="GenerationSpanData")
        span.span_data = gen_span_data
        span.trace_id = "test_trace_123"
        span.span_id = "test_span_456"
        span.parent_id = "test_parent_789"
        span.group_id = "test_group_123"
        
        # Create a direct processor with its exporter
        processor = OpenAIAgentsProcessor()
        processor.exporter = OpenAIAgentsExporter()
        
        # Create a capture mechanism for export
        attributes_dict = {}
        original_create_span = processor.exporter._create_span
        
        def mock_create_span(tracer, span_name, span_kind, attributes, span):
            # Capture the attributes for validation
            attributes_dict.update(attributes)
            # Don't actually create the span to avoid complexity
            return None
            
        # Replace with our capturing function
        processor.exporter._create_span = mock_create_span
        
        # Process the span
        processor.exporter._export_span(span)
        
        # Copy captured attributes to our test dictionary
        captured_attributes.update(attributes_dict)
        
        # Verify the captured attributes contain key information
        assert SpanAttributes.LLM_REQUEST_MODEL in captured_attributes
        assert captured_attributes[SpanAttributes.LLM_REQUEST_MODEL] == REAL_OPENAI_RESPONSE["model"]
        
        # Verify system is correct
        assert SpanAttributes.LLM_SYSTEM in captured_attributes
        assert captured_attributes[SpanAttributes.LLM_SYSTEM] == "openai"
        
        # Verify model settings were captured
        assert SpanAttributes.LLM_REQUEST_TEMPERATURE in captured_attributes
        assert captured_attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] == 0.7
        
        assert SpanAttributes.LLM_REQUEST_TOP_P in captured_attributes  
        assert captured_attributes[SpanAttributes.LLM_REQUEST_TOP_P] == 1.0
        
        # Verify token usage was captured
        assert SpanAttributes.LLM_USAGE_TOTAL_TOKENS in captured_attributes
        assert captured_attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == REAL_OPENAI_RESPONSE["usage"]["total_tokens"]
        
        # Verify content was extracted using MessageAttributes
        content_attr = MessageAttributes.COMPLETION_CONTENT.format(i=0)
        assert content_attr in captured_attributes
        assert captured_attributes[content_attr] == REAL_OPENAI_RESPONSE["output"][0]["content"][0]["text"]
        
        # ADDITIONAL VALIDATIONS FOR AVAILABLE DATA NOT IN OUTPUT:
        
        # 1. Verify trace and span IDs are being captured correctly
        assert CoreAttributes.TRACE_ID in captured_attributes
        assert captured_attributes[CoreAttributes.TRACE_ID] == "test_trace_123"
        assert CoreAttributes.SPAN_ID in captured_attributes
        assert captured_attributes[CoreAttributes.SPAN_ID] == "test_span_456"
        assert CoreAttributes.PARENT_ID in captured_attributes
        assert captured_attributes[CoreAttributes.PARENT_ID] == "test_parent_789"
        
        # 2. Verify tools are being captured
        assert AgentAttributes.AGENT_TOOLS in captured_attributes
        assert captured_attributes[AgentAttributes.AGENT_TOOLS] == "web_search,calculator"
        
        # 3. Verify agent name is captured
        assert AgentAttributes.FROM_AGENT in captured_attributes
        assert captured_attributes[AgentAttributes.FROM_AGENT] == agent_name
        
        # 4. Verify output type is accessible
        assert "output_type" in dir(gen_span_data)
        assert gen_span_data.output_type == "text"
        
        # 5. Verify library version is always a string (previously fixed issue)
        assert InstrumentationAttributes.LIBRARY_VERSION in captured_attributes
        assert isinstance(captured_attributes[InstrumentationAttributes.LIBRARY_VERSION], str)
        
        # 6. Verify we have required resource attributes that should be included
        assert InstrumentationAttributes.LIBRARY_NAME in captured_attributes
        assert captured_attributes[InstrumentationAttributes.LIBRARY_NAME] == LIBRARY_NAME
        
    def test_process_agent_span(self, instrumentation):
        """Test processing of Agent spans in the exporter."""
        # Create a dictionary to capture attributes
        captured_attributes = {}
        
        # Create an agent span data with the signature that the class accepts
        agent_span_data = AgentSpanData(
            name="test_agent",
            tools=["tool1", "tool2"]
        )
        
        # Add additional attributes that our exporter looks for
        agent_span_data.from_agent = "source_agent"
        agent_span_data.to_agent = "target_agent"  
        agent_span_data.input = "What is the capital of France?"
        agent_span_data.output = "Paris is the capital of France"
        
        # Create a mock span with the span data
        mock_span = MockSpan({}, span_type="AgentSpanData")
        mock_span.span_data = agent_span_data
        mock_span.trace_id = "trace123"
        mock_span.span_id = "span456"
        mock_span.parent_id = "parent789"
        
        # Initialize the exporter
        exporter = OpenAIAgentsExporter()
        
        # Create a mock _create_span method to capture attributes
        def mock_create_span(tracer, span_name, span_kind, attributes, span):
            captured_attributes.update(attributes)
            return None
            
        # Replace with our mock method
        original_create_span = exporter._create_span
        exporter._create_span = mock_create_span
        
        try:
            # Process the span
            exporter._export_span(mock_span)
            
            # Verify attributes were correctly set
            assert AgentAttributes.AGENT_NAME in captured_attributes
            assert captured_attributes[AgentAttributes.AGENT_NAME] == "test_agent"
            assert AgentAttributes.AGENT_TOOLS in captured_attributes
            assert captured_attributes[AgentAttributes.AGENT_TOOLS] == "tool1,tool2"
            assert AgentAttributes.FROM_AGENT in captured_attributes
            assert captured_attributes[AgentAttributes.FROM_AGENT] == "source_agent"
            assert AgentAttributes.TO_AGENT in captured_attributes
            assert captured_attributes[AgentAttributes.TO_AGENT] == "target_agent"
            assert WorkflowAttributes.WORKFLOW_INPUT in captured_attributes
            assert captured_attributes[WorkflowAttributes.WORKFLOW_INPUT] == "What is the capital of France?"
            assert WorkflowAttributes.FINAL_OUTPUT in captured_attributes
            assert captured_attributes[WorkflowAttributes.FINAL_OUTPUT] == "Paris is the capital of France"
            assert CoreAttributes.TRACE_ID in captured_attributes
            assert captured_attributes[CoreAttributes.TRACE_ID] == "trace123"
            assert CoreAttributes.SPAN_ID in captured_attributes
            assert captured_attributes[CoreAttributes.SPAN_ID] == "span456"
            assert CoreAttributes.PARENT_ID in captured_attributes
            assert captured_attributes[CoreAttributes.PARENT_ID] == "parent789"
            
            # Verify our new completion content and role attributes (added in our bugfix)
            completion_content_attr = MessageAttributes.COMPLETION_CONTENT.format(i=0)
            completion_role_attr = MessageAttributes.COMPLETION_ROLE.format(i=0)
            assert completion_content_attr in captured_attributes
            assert captured_attributes[completion_content_attr] == "Paris is the capital of France"
            assert completion_role_attr in captured_attributes
            assert captured_attributes[completion_role_attr] == "assistant"
        finally:
            # Restore original method
            exporter._create_span = original_create_span
    
    def test_process_chat_completions(self, instrumentation):
        """Test processing of chat completions in the exporter using real fixtures."""
        # Create dictionaries to capture attributes
        captured_attributes_standard = {}
        captured_attributes_tool_calls = {}
        
        # Initialize the exporter
        exporter = OpenAIAgentsExporter()
        
        # Process the standard chat completion fixture
        exporter._process_chat_completions(OPENAI_CHAT_COMPLETION, captured_attributes_standard)
        
        # Verify standard chat completion attributes were correctly set using MessageAttributes
        assert MessageAttributes.COMPLETION_CONTENT.format(i=0) in captured_attributes_standard
        assert captured_attributes_standard[MessageAttributes.COMPLETION_CONTENT.format(i=0)] == "The capital of France is Paris."
        assert MessageAttributes.COMPLETION_ROLE.format(i=0) in captured_attributes_standard
        assert captured_attributes_standard[MessageAttributes.COMPLETION_ROLE.format(i=0)] == "assistant"
        assert MessageAttributes.COMPLETION_FINISH_REASON.format(i=0) in captured_attributes_standard
        assert captured_attributes_standard[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] == "stop"
        
        # Process the tool calls chat completion fixture
        exporter._process_chat_completions(OPENAI_CHAT_TOOL_CALLS, captured_attributes_tool_calls)
        
        # Verify tool calls attributes were correctly set using MessageAttributes
        assert MessageAttributes.COMPLETION_ROLE.format(i=0) in captured_attributes_tool_calls
        assert captured_attributes_tool_calls[MessageAttributes.COMPLETION_ROLE.format(i=0)] == "assistant"
        assert MessageAttributes.COMPLETION_FINISH_REASON.format(i=0) in captured_attributes_tool_calls
        assert captured_attributes_tool_calls[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] == "tool_calls"
        
        # Verify content is an empty string when null in the fixture
        assert MessageAttributes.COMPLETION_CONTENT.format(i=0) in captured_attributes_tool_calls
        assert captured_attributes_tool_calls[MessageAttributes.COMPLETION_CONTENT.format(i=0)] == ""
        
        # Verify tool calls were processed correctly using MessageAttributes
        tool_call_id_attr = MessageAttributes.TOOL_CALL_ID.format(i=0, j=0)
        assert tool_call_id_attr in captured_attributes_tool_calls
        assert captured_attributes_tool_calls[tool_call_id_attr] == "call_EKUsxI7LNqe2beBJlNAGNsd3"
        
        tool_call_name_attr = MessageAttributes.TOOL_CALL_NAME.format(i=0, j=0)
        assert tool_call_name_attr in captured_attributes_tool_calls
        assert captured_attributes_tool_calls[tool_call_name_attr] == "get_weather"
        
        tool_call_args_attr = MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0, j=0)
        assert tool_call_args_attr in captured_attributes_tool_calls
        assert captured_attributes_tool_calls[tool_call_args_attr] == '{"location":"San Francisco, CA","unit":"celsius"}'
        assert "San Francisco" in captured_attributes_tool_calls[tool_call_args_attr]
    
    def test_process_function_span(self, instrumentation):
        """Test processing of Function spans in the exporter."""
        # Create a dictionary to capture attributes
        captured_attributes = {}
        
        # Extract function call data from the fixture
        tool_call = REAL_OPENAI_TOOL_CALLS_RESPONSE["output"][0]
        
        # Create a function span data with the signature that the class accepts, using fixture data
        function_span_data = FunctionSpanData(
            name=tool_call["name"],
            input=tool_call["arguments"],
            output=f"The weather in San Francisco, CA is 22 degrees celsius."
        )
        
        # Add additional attributes that our exporter looks for
        function_span_data.from_agent = "assistant"
        function_span_data.tools = ["weather_tool"]
        
        # Create a mock span with the span data
        mock_span = MockSpan({}, span_type="FunctionSpanData")
        mock_span.span_data = function_span_data
        mock_span.trace_id = REAL_OPENAI_TOOL_CALLS_RESPONSE["id"]
        mock_span.span_id = tool_call["id"]
        mock_span.parent_id = "parent_func_789"
        
        # Initialize the exporter
        exporter = OpenAIAgentsExporter()
        
        # Create a mock _create_span method to capture attributes
        def mock_create_span(tracer, span_name, span_kind, attributes, span):
            captured_attributes.update(attributes)
            return None
            
        # Replace with our mock method
        original_create_span = exporter._create_span
        exporter._create_span = mock_create_span
        
        try:
            # Process the span
            exporter._export_span(mock_span)
            
            # Verify attributes were correctly set
            assert AgentAttributes.AGENT_NAME in captured_attributes
            assert isinstance(captured_attributes[AgentAttributes.AGENT_NAME], str)
            assert AgentAttributes.AGENT_TOOLS in captured_attributes
            assert isinstance(captured_attributes[AgentAttributes.AGENT_TOOLS], str)
            assert AgentAttributes.FROM_AGENT in captured_attributes
            assert isinstance(captured_attributes[AgentAttributes.FROM_AGENT], str)
            assert SpanAttributes.LLM_PROMPTS in captured_attributes
            assert isinstance(captured_attributes[SpanAttributes.LLM_PROMPTS], str)
            # We don't check for LLM_COMPLETIONS as we no longer set it directly per serialization rules
            assert CoreAttributes.TRACE_ID in captured_attributes
            assert CoreAttributes.SPAN_ID in captured_attributes
            assert CoreAttributes.PARENT_ID in captured_attributes
        finally:
            # Restore original method
            exporter._create_span = original_create_span
    
    def test_error_handling_in_spans(self, instrumentation):
        """Test handling of spans with errors."""
        from opentelemetry.trace import Status, StatusCode
        
        # Create a simple generation span
        model_settings = ModelSettings(temperature=0.7, top_p=1.0)
        
        gen_span_data = GenerationSpanData(
            model="gpt-4o",
            model_config=model_settings,
            input="What's the weather in San Francisco?",
            output="The weather in San Francisco is foggy and 65°F.",
            usage={"input_tokens": 10, "output_tokens": 10, "total_tokens": 20}
        )
        
        # Create a span with error
        mock_span = MagicMock()
        mock_span.span_data = gen_span_data
        mock_span.trace_id = "trace123"
        mock_span.span_id = "span456"
        mock_span.parent_id = "parent789"
        mock_span.error = {
            "message": "API request failed", 
            "data": {"code": "rate_limit_exceeded"}
        }
        
        # Create a mock for the otel span
        mock_otel_span = MagicMock()
        
        # Initialize the test environment
        with patch('opentelemetry.trace.Status', MagicMock()) as MockStatus:
            with patch('opentelemetry.trace.get_tracer', return_value=MagicMock()) as mock_get_tracer:
                # Create a mock to be returned by start_as_current_span
                mock_tracer = mock_get_tracer.return_value
                mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_otel_span
                
                # Initialize the exporter
                exporter = OpenAIAgentsExporter()
                
                # Call the original method
                exporter._create_span(mock_tracer, "test_span", None, {}, mock_span)
                
                # Verify error handling calls
                mock_otel_span.set_status.assert_called_once()
                mock_otel_span.record_exception.assert_called_once()
    
    def test_trace_export(self, instrumentation):
        """Test exporting of traces with spans."""
        # Create a dictionary to capture attributes
        captured_attributes = {}
        
        # Create a simple mock trace object
        mock_trace = MagicMock()
        mock_trace.name = "test_workflow"
        mock_trace.trace_id = "trace123"
        mock_trace.group_id = "group123"
        
        # Create a simple GenerationSpanData about SF weather
        model_settings = ModelSettings(temperature=0.7, top_p=1.0)
        
        gen_span_data = GenerationSpanData(
            model="gpt-4o",
            model_config=model_settings,
            input="What's the weather in San Francisco?",
            output="The weather in San Francisco is foggy and 65°F.",
            usage={"input_tokens": 10, "output_tokens": 10, "total_tokens": 20}
        )
        
        # Create a simple mock span
        mock_span = MockSpan({}, span_type="GenerationSpanData")
        mock_span.span_data = gen_span_data
        
        # Set up the mock trace with this span
        mock_trace.spans = [mock_span, MagicMock()]
        
        # Create a mock tracer
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        
        # Create an exporter with a mocked tracer_provider
        tracer_provider = MagicMock()
        
        # Initialize the exporter with this tracer provider
        exporter = OpenAIAgentsExporter(tracer_provider=tracer_provider)
        
        # Create a context manager for the mock_tracer
        mock_context_manager = mock_tracer.start_as_current_span.return_value.__enter__.return_value
        
        # We need to patch at the right location - the OpenAIAgentsExporter module
        with patch('agentops.instrumentation.openai_agents.exporter.get_tracer', return_value=mock_tracer):
            # Export the trace
            exporter.export_trace(mock_trace)
            
            # Verify span was created with correct attributes
            mock_tracer.start_as_current_span.assert_called_once()
            call_args = mock_tracer.start_as_current_span.call_args[1]
            assert 'name' in call_args
            assert call_args['name'] == f"agents.trace.{mock_trace.name}"
            
            assert 'attributes' in call_args
            attributes = call_args['attributes']
            assert WorkflowAttributes.WORKFLOW_NAME in attributes
            assert attributes[WorkflowAttributes.WORKFLOW_NAME] == "test_workflow"
            assert CoreAttributes.TRACE_ID in attributes
            assert attributes[CoreAttributes.TRACE_ID] == "trace123"
            assert InstrumentationAttributes.LIBRARY_NAME in attributes
        
    def test_instrumentor_patching(self, instrumentation):
        """Test the OpenAIAgentsInstrumentor's ability to capture agent attributes."""
        # Create a mock agent with instructions
        agent = Agent(
            name="instruction_test_agent",
            instructions="You are a helpful assistant. Your task is to answer questions."
        )
        
        # Initialize the instrumentor
        instrumentor = OpenAIAgentsInstrumentor()
        
        # Create a dictionary to capture attributes
        captured_attributes = {}
        
        # Create mock span
        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock(side_effect=lambda k, v: captured_attributes.update({k: v}))
        
        # Call the method to test instructions
        instrumentor._add_agent_attributes_to_span(mock_span, agent)
        
        # Verify instructions were set as agent attributes
        assert "agent.instructions" in captured_attributes
        assert captured_attributes["agent.instructions"] == "You are a helpful assistant. Your task is to answer questions."
        assert "agent.instruction_type" in captured_attributes
        assert captured_attributes["agent.instruction_type"] == "string"
        
        # Verify instructions were also set as gen_ai.prompt (our bugfix)
        assert SpanAttributes.LLM_PROMPTS in captured_attributes
        assert captured_attributes[SpanAttributes.LLM_PROMPTS] == "You are a helpful assistant. Your task is to answer questions."
    
    def test_get_model_info_function(self, instrumentation):
        """Test the get_model_info function with various inputs."""
        # Test with an agent that has model and model_settings
        agent = Agent(
            name="test_agent", 
            instructions="You are a helpful assistant.",
            model="gpt-4o",
            model_settings=ModelSettings(
                temperature=0.8,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.2
            )
        )
        
        # No run config
        model_info = get_model_info(agent, None)
        
        # Verify model info was extracted correctly
        assert "model_name" in model_info
        assert model_info["model_name"] == "gpt-4o"
        assert "temperature" in model_info
        assert model_info["temperature"] == 0.8
        assert "top_p" in model_info
        assert model_info["top_p"] == 0.9
        assert "frequency_penalty" in model_info
        assert model_info["frequency_penalty"] == 0.1
        assert "presence_penalty" in model_info
        assert model_info["presence_penalty"] == 0.2
        
        # Test with run config that overrides agent model
        run_config = RunConfig(
            model="gpt-3.5-turbo",
            model_settings=ModelSettings(temperature=0.5)
        )
        
        # Run with config
        model_info_with_config = get_model_info(agent, run_config)
        
        # Verify run config overrides agent settings
        assert "model_name" in model_info_with_config
        assert model_info_with_config["model_name"] == "gpt-3.5-turbo"
        assert "temperature" in model_info_with_config
        assert model_info_with_config["temperature"] == 0.5
        # These should still come from the agent
        assert "top_p" in model_info_with_config
        assert model_info_with_config["top_p"] == 0.9
    
    def _find_span_by_trace_id(self, spans, trace_id):
        """Helper method to find a span with a specific trace ID."""
        for span in spans:
            # Use semantic convention for trace ID
            if span.attributes.get(CoreAttributes.TRACE_ID) == trace_id:
                return span
        return None
        
    def test_child_nodes_inherit_attributes(self, instrumentation):
        """Test that child nodes (function spans and generation spans) inherit necessary attributes.
        
        This test verifies the fix for the issue where child nodes weren't showing expected content.
        """
        # Create a dictionary to capture attributes
        captured_attributes = {}
        
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create function span data for a child node
        function_span_data = FunctionSpanData(
            name="get_weather",
            input='{"location":"San Francisco, CA"}',
            output="The weather in San Francisco is sunny and 75°F."
        )
        
        # Create a mock span with the function span data
        mock_span = MockSpan({}, span_type="FunctionSpanData")
        mock_span.span_data = function_span_data
        mock_span.trace_id = "child_trace_123"
        mock_span.span_id = "child_span_456"
        mock_span.parent_id = "parent_span_789"
        
        # Process the mock span with the OpenAI Agents exporter
        with tracer.start_as_current_span("test_child_node_attributes") as span:
            process_with_instrumentor(mock_span, OpenAIAgentsExporter, captured_attributes)
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes.items():
                span.set_attribute(key, val)
        
        # Get all spans
        spans = instrumentation.get_finished_spans()
        
        # Find all spans with our trace ID
        for span in spans:
            if "agents.function" in span.name and span.attributes.get(CoreAttributes.TRACE_ID) == "child_trace_123":
                child_span = span
                break
        else:
            child_span = None
            
        assert child_span is not None, "Failed to find the child node function span"
        
        # Verify the child span has all essential attributes
        # 1. It should have gen_ai.prompt (LLM_PROMPTS)
        assert SpanAttributes.LLM_PROMPTS in child_span.attributes, "Child span missing prompt attribute"
        
        # 2. It should have a completion content attribute
        completion_attr = MessageAttributes.COMPLETION_CONTENT.format(i=0)
        assert completion_attr in child_span.attributes, "Child span missing completion content attribute"
        assert "weather in San Francisco" in child_span.attributes[completion_attr], "Completion content doesn't match expected output"
        
        # 3. It should have a completion role attribute
        role_attr = MessageAttributes.COMPLETION_ROLE.format(i=0)
        assert role_attr in child_span.attributes, "Child span missing completion role attribute"
        
        # 4. It should have workflow input attribute
        assert WorkflowAttributes.WORKFLOW_INPUT in child_span.attributes, "Child span missing workflow input attribute"
        
        # 5. It should have workflow final output attribute
        assert WorkflowAttributes.FINAL_OUTPUT in child_span.attributes, "Child span missing workflow final output attribute"

    def test_generation_span_with_chat_completion(self, instrumentation):
        """Test processing of generation spans with Chat Completion API format."""
        # Dictionary to capture attributes from the instrumentor
        captured_attributes = {}
        
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span for our test
        with tracer.start_as_current_span("test_chat_completion_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "client")
            
            # Create model settings
            model_settings = ModelSettings(
                temperature=OPENAI_CHAT_COMPLETION.get("temperature", 0.7),
                top_p=OPENAI_CHAT_COMPLETION.get("top_p", 1.0)
            )
            
            # Create span data using the chat completion fixture
            gen_span_data = GenerationSpanData(
                model=OPENAI_CHAT_COMPLETION["model"],
                model_config=model_settings,
                input="What is the capital of France?",
                output=OPENAI_CHAT_COMPLETION,
                usage=OPENAI_CHAT_COMPLETION["usage"]
            )
            
            # Create a mock span with our prepared data
            mock_span = MockSpan({}, span_type="GenerationSpanData")
            mock_span.span_data = gen_span_data
            mock_span.trace_id = "trace123"
            mock_span.span_id = "span456"
            mock_span.parent_id = "parent789"
            
            # Process the mock span with the actual OpenAIAgentsExporter
            process_with_instrumentor(mock_span, OpenAIAgentsExporter, captured_attributes)
            
            # Print captured attributes for debugging
            print(f"DEBUG captured_attributes: {captured_attributes}")
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes.items():
                span.set_attribute(key, val)
        
        # Get all spans
        spans = instrumentation.get_finished_spans()
        
        # Find the generation span to verify all attributes were set correctly
        for span in spans:
            if span.name == "agents.generation":
                generation_span = span
                break
        else:
            generation_span = None
            
        assert generation_span is not None, "Failed to find the generation span"
        
        # Test expected attributes on the generation span itself instead of captured_attributes
        expected_key_attributes = {
            SpanAttributes.LLM_REQUEST_MODEL: OPENAI_CHAT_COMPLETION["model"],
            SpanAttributes.LLM_SYSTEM: "openai", 
            MessageAttributes.COMPLETION_CONTENT.format(i=0): "The capital of France is Paris."
        }
        
        # Check required attributes exist on the generation span
        for key, expected_value in expected_key_attributes.items():
            assert key in generation_span.attributes, f"Missing expected attribute '{key}' in generation span"
            assert generation_span.attributes[key] == expected_value, f"Wrong value for {key} in generation span"
        
        # Check more attributes on the generation span
        assert MessageAttributes.COMPLETION_ROLE.format(i=0) in generation_span.attributes
        assert generation_span.attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] == "assistant"
        
        assert MessageAttributes.COMPLETION_FINISH_REASON.format(i=0) in generation_span.attributes
        assert generation_span.attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] == "stop"
        
        assert MessageAttributes.COMPLETION_CONTENT.format(i=0) in generation_span.attributes
        assert generation_span.attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] == "The capital of France is Paris."
                
        # Test with the tool calls completion
        captured_attributes_tool = {}
        
        # Create a new span for the tool calls test
        with tracer.start_as_current_span("test_chat_tool_calls_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "client")
            
            # Create span data using the chat tool calls fixture
            gen_span_data = GenerationSpanData(
                model=OPENAI_CHAT_TOOL_CALLS["model"],
                model_config=model_settings,
                input="What's the weather in San Francisco?",
                output=OPENAI_CHAT_TOOL_CALLS,
                usage=OPENAI_CHAT_TOOL_CALLS["usage"]
            )
            
            # Create a mock span with our prepared data
            mock_span = MockSpan({}, span_type="GenerationSpanData")
            mock_span.span_data = gen_span_data
            mock_span.trace_id = "tool_trace123"
            mock_span.span_id = "tool_span456"
            
            # Process the mock span with the actual OpenAIAgentsExporter
            process_with_instrumentor(mock_span, OpenAIAgentsExporter, captured_attributes_tool)
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes_tool.items():
                span.set_attribute(key, val)
                
        # Get all spans
        tool_spans = instrumentation.get_finished_spans()
        
        # Find the span with the right trace ID for tool calls
        tool_instrumented_span = self._find_span_by_trace_id(tool_spans, "tool_trace123")
        
        # Ensure we found the right span
        assert tool_instrumented_span is not None, "Failed to find the tool calls generation span"
        
        # Verify tool calls were correctly processed using MessageAttributes
        tool_id_attr = MessageAttributes.TOOL_CALL_ID.format(i=0, j=0)
        tool_name_attr = MessageAttributes.TOOL_CALL_NAME.format(i=0, j=0)
        tool_args_attr = MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0, j=0)
        
        assert tool_id_attr in tool_instrumented_span.attributes
        assert tool_name_attr in tool_instrumented_span.attributes
        assert tool_args_attr in tool_instrumented_span.attributes
        
        # Verify the specific tool call values
        assert tool_instrumented_span.attributes[tool_id_attr] == "call_EKUsxI7LNqe2beBJlNAGNsd3"
        assert tool_instrumented_span.attributes[tool_name_attr] == "get_weather"
        assert "San Francisco" in tool_instrumented_span.attributes[tool_args_attr]

    def test_processor_integration_with_agent_tracing(self, instrumentation):
        """Test the integration of OpenAIAgentsProcessor with the Agents SDK tracing system."""
        # Create the processor directly
        processor = OpenAIAgentsProcessor()
        assert isinstance(processor, OpenAIAgentsProcessor)
        
        # Verify the processor has the correct methods
        assert hasattr(processor, 'on_span_start')
        assert hasattr(processor, 'on_span_end')
        assert hasattr(processor, 'on_trace_start')
        assert hasattr(processor, 'on_trace_end')
        
        # Initialize the exporter
        processor.exporter = OpenAIAgentsExporter()
        assert isinstance(processor.exporter, OpenAIAgentsExporter)
        
        # Create a capture mechanism for export calls
        exported_spans = []
        
        # Replace with our capturing methods
        processor.exporter.export_span = lambda span: exported_spans.append(span)
        processor.exporter.export_trace = lambda trace: exported_spans.append(trace)
        
        # Create simple span data about SF weather
        model_settings = ModelSettings(temperature=0.7, top_p=1.0)
        
        gen_span_data = GenerationSpanData(
            model="gpt-4o",
            model_config=model_settings,
            input="What's the weather in San Francisco?",
            output="The weather in San Francisco is foggy and 65°F.",
            usage={"input_tokens": 10, "output_tokens": 10, "total_tokens": 20}
        )
            
        # Create a simple mock span
        span = MockSpan({}, span_type="GenerationSpanData")
        span.span_data = gen_span_data
        span.trace_id = "trace123"
        span.span_id = "span456"
        span.parent_id = "parent789"
        
        # Call the processor's on_span_end method
        processor.on_span_end(span)
        
        # Verify the span was exported
        assert len(exported_spans) == 1
        assert exported_spans[0] == span
        
        # Test the other processor methods for coverage
        processor.on_span_start(span)
        assert len(exported_spans) == 2
        
        # Create a simple mock trace
        mock_trace = MagicMock()
        mock_trace.name = "test_trace"
        mock_trace.trace_id = "trace123" 
        mock_trace.group_id = "group123"
        mock_trace.spans = [span]
        
        # Test trace methods
        processor.on_trace_start(mock_trace)
        assert len(exported_spans) == 3
        
        processor.on_trace_end(mock_trace)
        assert len(exported_spans) == 4
        
        # Test shutdown and force_flush for coverage
        processor.shutdown()
        processor.force_flush()
    
    def test_capturing_timestamps_and_events(self, instrumentation):
        """
        Test that the processor and exporter correctly capture and handle 
        timestamps and events that are currently missing from the output.
        """
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span for testing
        with tracer.start_as_current_span("test_timestamps_and_events") as test_span:
            # Set the span type
            test_span.set_attribute("span.kind", "client")
            
            # 1. Test timestamp handling
            start_time = time.time()
            time.sleep(0.001)  # Ensure some time passes
            end_time = time.time()
            
            # Dictionary to capture span attributes
            captured_attributes = {}
            
            # Create model settings
            model_settings = ModelSettings(temperature=0.7, top_p=1.0)
            
            # Create event data that should be captured
            events = [
                {"event_type": "agent_start", "timestamp": start_time},
                {"event_type": "llm_request", "timestamp": start_time + 0.0005},
                {"event_type": "agent_end", "timestamp": end_time}
            ]
            
            # Create a span data object with timestamps and events
            gen_span_data = GenerationSpanData(
                model="gpt-4o",
                model_config=model_settings,
                input="What's the weather in San Francisco?",
                output="The weather in San Francisco is foggy and 65°F.",
                usage={"input_tokens": 10, "output_tokens": 10, "total_tokens": 20}
            )
            
            # Add timing and event information
            span = MockSpan({}, span_type="GenerationSpanData")
            span.span_data = gen_span_data
            span.trace_id = "timing_trace123"
            span.span_id = "timing_span456"
            span.parent_id = "timing_parent789"
            span.start_time = start_time
            span.end_time = end_time
            span.events = events
            span.duration = end_time - start_time
            
            # Process the mock span with the actual OpenAIAgentsExporter
            original_create_span = OpenAIAgentsExporter._create_span
            span_data_captured = {}
            
            def mock_create_span(self, tracer, span_name, span_kind, attributes, span):
                # Capture the span timing information
                span_data_captured.update({
                    "name": span_name,
                    "kind": span_kind,
                    "attributes": attributes.copy(),
                    "span": span
                })
                # Capture the attributes for validation
                captured_attributes.update(attributes)
                # Don't actually create the span to avoid complexity
                return None
                
            # Apply our mock
            OpenAIAgentsExporter._create_span = mock_create_span
            
            try:
                # Create an exporter instance
                exporter = OpenAIAgentsExporter()
                
                # Export the span with all the timing and event data
                exporter._export_span(span)
                
                # Verify the results
                assert "name" in span_data_captured
                assert span_data_captured["name"] == "agents.generation"
                
                # Verify all basic attributes were captured
                assert CoreAttributes.TRACE_ID in captured_attributes
                assert captured_attributes[CoreAttributes.TRACE_ID] == "timing_trace123"
                assert CoreAttributes.SPAN_ID in captured_attributes
                assert captured_attributes[CoreAttributes.SPAN_ID] == "timing_span456"
                assert CoreAttributes.PARENT_ID in captured_attributes
                assert captured_attributes[CoreAttributes.PARENT_ID] == "timing_parent789"
                
                # Verify the exporter has access to timing data
                assert hasattr(span, 'start_time')
                assert hasattr(span, 'end_time')
                assert hasattr(span, 'duration')
                
                # 2. Verify events data is available but not used
                assert hasattr(span, 'events')
                assert len(span.events) == 3
                assert span.events[0]["event_type"] == "agent_start"
                assert span.events[1]["event_type"] == "llm_request"
                assert span.events[2]["event_type"] == "agent_end"
                
                # 3. Check that the OpenTelemetry span would have access to all this data
                # Even though it's not being passed through to the output JSON
                
                # Set all the data on our test span so we can validate it
                for attr, value in captured_attributes.items():
                    test_span.set_attribute(attr, value)
                
                # Manually set attributes that should be set in the OpenTelemetry span
                test_span.set_attribute("start_time", start_time)
                test_span.set_attribute("end_time", end_time)
                test_span.set_attribute("duration", end_time - start_time)
                
                # Add events to the test span
                for event in events:
                    test_span.add_event(event["event_type"], {"timestamp": event["timestamp"]})
                                
            finally:
                # Restore the original method
                OpenAIAgentsExporter._create_span = original_create_span
                
        # Get all spans
        spans = instrumentation.get_finished_spans()
        
        # Find the test span
        test_span = None
        for span in spans:
            if span.name == "test_timestamps_and_events":
                test_span = span
                break
                
        assert test_span is not None, "Failed to find the test span"
        
        # Verify that our test span has all the data that the exporter has access to
        # These tests demonstrate that the data is available but not being included in the output
        assert CoreAttributes.TRACE_ID in test_span.attributes
        assert CoreAttributes.SPAN_ID in test_span.attributes
        assert CoreAttributes.PARENT_ID in test_span.attributes
        
        # Make sure the events were properly recorded
        assert len(test_span.events) == 3
        event_types = [event.name for event in test_span.events]
        assert "agent_start" in event_types
        assert "llm_request" in event_types
        assert "agent_end" in event_types
    
    def test_attributes_field_population(self, instrumentation):
        """
        Test that validates data should be in the 'attributes' field of the output JSON.
        Currently this field is empty but it should contain non-semantic convention attributes.
        """
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create model settings
        model_settings = ModelSettings(temperature=0.7, top_p=1.0)
        
        # Create a span data object with additional custom attributes
        gen_span_data = GenerationSpanData(
            model="gpt-4o",
            model_config=model_settings,
            input="What's the capital of France?",
            output="Paris is the capital of France.",
            usage={"input_tokens": 10, "output_tokens": 6, "total_tokens": 16}
        )
        
        # Add custom attributes that should go in the attributes field
        # but not in span_attributes (non-semantic conventions)
        custom_attributes = {
            "custom.attribute.1": "value1",
            "custom.attribute.2": 123,
            "execution.environment": "test",
            "non.standard.field": True
        }
        
        # Create test span with our MockSpan
        span = MockSpan({}, span_type="GenerationSpanData")
        span.span_data = gen_span_data
        span.trace_id = "attrs_trace123"
        span.span_id = "attrs_span456"
        span.parent_id = "attrs_parent789"
        
        # Add custom attributes to span
        for key, value in custom_attributes.items():
            setattr(span, key, value)
        
        # Manually add custom_attributes dictionary
        span.custom_attributes = custom_attributes
        
        # Dictionary to capture span attributes
        captured_attributes = {}
        
        # Process the mock span with the actual OpenAIAgentsExporter
        original_create_span = OpenAIAgentsExporter._create_span
        all_data_captured = {}
        
        def mock_create_span(self, tracer, span_name, span_kind, attributes, span):
            # Capture everything for validation
            all_data_captured.update({
                "name": span_name,
                "kind": span_kind,
                "attributes": attributes.copy(),
                "span": span,
                "custom_attributes": getattr(span, "custom_attributes", {})
            })
            # Capture the attributes for validation
            captured_attributes.update(attributes)
            # Return None to avoid creating actual span
            return None
            
        # Apply our mock
        OpenAIAgentsExporter._create_span = mock_create_span
        
        try:
            # Create an exporter instance
            exporter = OpenAIAgentsExporter()
            
            # Export the span with all the custom attributes
            exporter._export_span(span)
            
            # Verify that custom attributes are available for processing
            assert hasattr(span, "custom_attributes")
            assert span.custom_attributes == custom_attributes
            
            # Examine captured data to see if there's a path to include these in "attributes" JSON field
            assert "custom_attributes" in all_data_captured
            assert len(all_data_captured["custom_attributes"]) == 4
            
            # This test demonstrates that custom attributes are available
            # but not being included in the output "attributes" field 
            # in api_output.json which is currently empty: "attributes": {}
            for key, value in custom_attributes.items():
                # The current implementation doesn't add these to semantic attributes
                # That's correct behavior, but they should go in "attributes" field
                assert key not in captured_attributes, f"Unexpected: {key} found in semantic attributes"
                
        finally:
            # Restore the original method
            OpenAIAgentsExporter._create_span = original_create_span
            
        # This test verifies that we have access to additional attributes
        # that should be included in the "attributes" field of the output JSON,
        # which is currently empty
