"""
Tests for OpenAI Agents SDK Instrumentation

This module contains tests for properly handling and serializing data from the OpenAI Agents SDK.
It verifies that our instrumentation correctly captures and instruments agent runs, tool usage,
and other operations specific to the OpenAI Agents SDK.

The Agents SDK has its own unique structure with:
- Agent runs with specific attributes and properties
- Tool calls and agent handoffs
- Raw responses that may contain either ChatCompletion or Response API objects
"""

import json
import os
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
    InstrumentationAttributes
)
from tests.unit.sdk.instrumentation_tester import InstrumentationTester
from agentops.instrumentation.openai_agents.exporter import OpenAIAgentsExporter
# These are in separate modules, import directly from those
from agentops.instrumentation.openai_agents.processor import OpenAIAgentsProcessor
from agentops.instrumentation.openai_agents.instrumentor import AgentsInstrumentor, get_model_info
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
        
        # Expected attribute values based on the fixture data
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
            
            # Content extraction with proper semantic conventions
            f"{SpanAttributes.LLM_COMPLETIONS}.0.content": REAL_OPENAI_RESPONSE["output"][0]["content"][0]["text"],
            f"{SpanAttributes.LLM_COMPLETIONS}.0.role": REAL_OPENAI_RESPONSE["output"][0]["role"],
        }
        
        # Check all required attributes from our reference model against the actual span
        for key, expected_value in expected_attributes.items():
            # Assert the attribute exists 
            assert key in instrumented_span.attributes, f"Missing expected attribute '{key}'"
            
            # Assert it has the expected value
            actual_value = instrumented_span.attributes[key]
            assert actual_value == expected_value, \
                f"Attribute '{key}' has wrong value. Expected: {expected_value}, Actual: {actual_value}"
                
        # Verify completions attributes
        completion_prefix = SpanAttributes.LLM_COMPLETIONS.split('.')[0]
        completion_attrs = [k for k in instrumented_span.attributes.keys() if k.startswith(completion_prefix)]
        expected_completion_attrs = [k for k in expected_attributes.keys() if k.startswith(completion_prefix)]
        
        # Make sure completion attributes match expected set
        for attr in expected_completion_attrs:
            assert attr in completion_attrs, f"Missing completion attribute: {attr}"
            
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
        
        # Expected attribute values based on the fixture data
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
            
            # Tool call details with proper semantic conventions
            f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.id": tool_call["id"],
            f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.name": tool_call["name"],
            f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.arguments": tool_call["arguments"]
        }
        
        # Check all required attributes from our reference model against the actual span
        for key, expected_value in expected_attributes.items():
            # Assert the attribute exists 
            assert key in instrumented_span.attributes, f"Missing expected attribute '{key}'"
            
            # Assert it has the expected value
            actual_value = instrumented_span.attributes[key]
            assert actual_value == expected_value, \
                f"Attribute '{key}' has wrong value. Expected: {expected_value}, Actual: {actual_value}"
        
        # Verify the tool calls attributes specifically
        tool_calls_prefix = f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls"
        tool_calls_attrs = [k for k in instrumented_span.attributes.keys() if k.startswith(tool_calls_prefix)]
        expected_tool_calls_attrs = [k for k in expected_attributes.keys() if k.startswith(tool_calls_prefix)]
        
        # Make sure we have all expected tool call attributes
        for attr in expected_tool_calls_attrs:
            assert attr in tool_calls_attrs, f"Missing tool call attribute: {attr}"
        
        # Verify specific tool call details
        tool_call_id_attr = f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.id"
        assert tool_call_id_attr in instrumented_span.attributes, f"Missing {tool_call_id_attr} attribute"
        assert instrumented_span.attributes[tool_call_id_attr] == tool_call["id"], "Incorrect tool call ID"
        
        tool_call_name_attr = f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.name"
        assert tool_call_name_attr in instrumented_span.attributes, f"Missing {tool_call_name_attr} attribute"
        assert instrumented_span.attributes[tool_call_name_attr] == tool_call["name"], "Incorrect tool call name"
        
        tool_call_args_attr = f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.arguments"
        assert tool_call_args_attr in instrumented_span.attributes, f"Missing {tool_call_args_attr} attribute"
        assert instrumented_span.attributes[tool_call_args_attr] == tool_call["arguments"], "Incorrect tool call arguments"
        assert "San Francisco" in instrumented_span.attributes[tool_call_args_attr], "Expected location not found in arguments"

    def test_full_agent_integration_with_real_types(self, instrumentation):
        """
        Test the full integration of the OpenAI Agents SDK with AgentOps.
        This test uses the real Agents SDK types and runs a simulated agent execution.
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
        
        # Mock the _export_span method
        def mock_export_span(span):
            # Extract span data
            captured_spans.append(span)
            
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
            
        # Create span data using the real SDK classes
        gen_span_data = GenerationSpanData(
            model=REAL_OPENAI_RESPONSE["model"],
            model_config=model_settings,
            input="What is the capital of France?",
            output=response,
            usage=REAL_OPENAI_RESPONSE["usage"]
        )
        
        # Create a span with our prepared data
        span = MockSpan({"data": gen_span_data}, span_type="GenerationSpanData")
        span.span_data = gen_span_data
        
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
        
        # Verify content was extracted
        content_attr = f"{SpanAttributes.LLM_COMPLETIONS}.0.content"
        assert content_attr in captured_attributes
        assert captured_attributes[content_attr] == REAL_OPENAI_RESPONSE["output"][0]["content"][0]["text"]
        
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
        
        # Verify standard chat completion attributes were correctly set
        assert f"{SpanAttributes.LLM_COMPLETIONS}.0.content" in captured_attributes_standard
        assert captured_attributes_standard[f"{SpanAttributes.LLM_COMPLETIONS}.0.content"] == "The capital of France is Paris."
        assert f"{SpanAttributes.LLM_COMPLETIONS}.0.role" in captured_attributes_standard
        assert captured_attributes_standard[f"{SpanAttributes.LLM_COMPLETIONS}.0.role"] == "assistant"
        assert f"{SpanAttributes.LLM_COMPLETIONS}.0.finish_reason" in captured_attributes_standard
        assert captured_attributes_standard[f"{SpanAttributes.LLM_COMPLETIONS}.0.finish_reason"] == "stop"
        
        # Process the tool calls chat completion fixture
        exporter._process_chat_completions(OPENAI_CHAT_TOOL_CALLS, captured_attributes_tool_calls)
        
        # Verify tool calls attributes were correctly set
        assert f"{SpanAttributes.LLM_COMPLETIONS}.0.role" in captured_attributes_tool_calls
        assert captured_attributes_tool_calls[f"{SpanAttributes.LLM_COMPLETIONS}.0.role"] == "assistant"
        assert f"{SpanAttributes.LLM_COMPLETIONS}.0.finish_reason" in captured_attributes_tool_calls
        assert captured_attributes_tool_calls[f"{SpanAttributes.LLM_COMPLETIONS}.0.finish_reason"] == "tool_calls"
        
        # Verify content is an empty string when null in the fixture
        assert f"{SpanAttributes.LLM_COMPLETIONS}.0.content" in captured_attributes_tool_calls
        assert captured_attributes_tool_calls[f"{SpanAttributes.LLM_COMPLETIONS}.0.content"] == ""
        
        # Verify tool calls were processed correctly
        tool_call_id = captured_attributes_tool_calls[f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.id"]
        assert tool_call_id == "call_EKUsxI7LNqe2beBJlNAGNsd3"
        
        tool_call_name = captured_attributes_tool_calls[f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.name"]
        assert tool_call_name == "get_weather"
        
        tool_call_args = captured_attributes_tool_calls[f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.arguments"]
        assert tool_call_args == '{"location":"San Francisco, CA","unit":"celsius"}'
        assert "San Francisco" in tool_call_args
    
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
            assert SpanAttributes.LLM_COMPLETIONS in captured_attributes
            assert isinstance(captured_attributes[SpanAttributes.LLM_COMPLETIONS], str)
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
        
        # Initialize the exporter
        exporter = OpenAIAgentsExporter()
        
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
        
        # Mock the get_tracer function
        with patch('agentops.instrumentation.openai_agents.exporter.get_tracer', return_value=mock_tracer):
            # Export the trace
            exporter._export_trace(mock_trace)
            
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
        """Test that the instrumentor properly patches the Runner class."""
        # Create a mock Runner class that matches the interface needed by the instrumentor
        class MockRunner:
            @classmethod
            def run_sync(cls, *args, **kwargs):
                return "original_run_sync"
            
            @classmethod 
            def run(cls, *args, **kwargs):
                return "original_run"
                
            @classmethod
            def run_streamed(cls, *args, **kwargs):
                return "original_run_streamed"
        
        # Create a patch to replace the actual Runner with our mock for testing
        with patch('agents.run.Runner', MockRunner):
            # Create a holder for the added processor
            added_processor = None
            
            # Mock the add_trace_processor function
            def mock_add_processor(processor):
                nonlocal added_processor
                added_processor = processor
                
            # Use mocking to avoid real SDK operations
            with patch('agents.add_trace_processor', mock_add_processor):
                # Initialize the instrumentor
                instrumentor = AgentsInstrumentor()
                
                # Store the original methods for verification
                original_run_sync = MockRunner.run_sync
                original_run = MockRunner.run
                original_run_streamed = MockRunner.run_streamed
                
                # Test the _instrument method
                instrumentor._patch_runner_class(None)  # We don't need a real tracer_provider for patching
                
                # We're not adding a processor in _patch_runner_class, so we don't need to verify it
                # Instead, let's verify the methods were replaced
                
                # Verify methods were replaced
                assert MockRunner.run_sync != original_run_sync
                assert MockRunner.run != original_run
                assert MockRunner.run_streamed != original_run_streamed
                
                # Verify original methods are stored
                assert "_original_methods" in instrumentor.__class__.__dict__
                assert instrumentor.__class__._original_methods["run_sync"] == original_run_sync
                assert instrumentor.__class__._original_methods["run"] == original_run
                assert instrumentor.__class__._original_methods["run_streamed"] == original_run_streamed
                
                # Test uninstrumentation
                instrumentor._uninstrument()
                
                # Verify methods were restored
                assert MockRunner.run_sync == original_run_sync
                assert MockRunner.run == original_run
                assert MockRunner.run_streamed == original_run_streamed
                
                # Verify methods dictionary is cleared
                assert not instrumentor.__class__._original_methods
    
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
        """Helper method to find a generation span with a specific trace ID."""
        for span in spans:
            if "gen_ai.request.model" in span.attributes and span.attributes.get("trace.id") == trace_id:
                return span
        return None

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
            
            # Process the mock span with the actual OpenAIAgentsExporter
            process_with_instrumentor(mock_span, OpenAIAgentsExporter, captured_attributes)
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes.items():
                span.set_attribute(key, val)
        
        # Get all spans
        spans = instrumentation.get_finished_spans()
            
        # Find the span with the right trace ID
        instrumented_span = self._find_span_by_trace_id(spans, "trace123")
        
        # Ensure we found the right span
        assert instrumented_span is not None, "Failed to find the regular chat completion span"
        
        # Expected attribute values based on the fixture data
        expected_attributes = {
            # Model metadata using semantic conventions
            SpanAttributes.LLM_REQUEST_MODEL: OPENAI_CHAT_COMPLETION["model"],
            SpanAttributes.LLM_SYSTEM: "openai",
            
            # Response metadata using semantic conventions
            SpanAttributes.LLM_RESPONSE_MODEL: OPENAI_CHAT_COMPLETION["model"],
            SpanAttributes.LLM_RESPONSE_ID: OPENAI_CHAT_COMPLETION["id"],
            SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT: OPENAI_CHAT_COMPLETION["system_fingerprint"],
            
            # Token usage with proper semantic conventions (mapping completion_tokens to output_tokens)
            SpanAttributes.LLM_USAGE_TOTAL_TOKENS: OPENAI_CHAT_COMPLETION["usage"]["total_tokens"],
            SpanAttributes.LLM_USAGE_PROMPT_TOKENS: OPENAI_CHAT_COMPLETION["usage"]["prompt_tokens"],
            SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: OPENAI_CHAT_COMPLETION["usage"]["completion_tokens"],
            
            # Message attributes
            f"{SpanAttributes.LLM_COMPLETIONS}.0.role": "assistant",
            f"{SpanAttributes.LLM_COMPLETIONS}.0.content": "The capital of France is Paris.",
            f"{SpanAttributes.LLM_COMPLETIONS}.0.finish_reason": "stop",
        }
        
        # Check all required attributes from our reference model against the actual span
        for key, expected_value in expected_attributes.items():
            # Assert the attribute exists
            assert key in instrumented_span.attributes, f"Missing expected attribute '{key}'"
            
            # Assert it has the expected value
            actual_value = instrumented_span.attributes[key]
            assert actual_value == expected_value, \
                f"Attribute '{key}' has wrong value. Expected: {expected_value}, Actual: {actual_value}"
                
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
        
        # Verify tool calls were correctly processed
        assert f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.id" in tool_instrumented_span.attributes
        assert f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.name" in tool_instrumented_span.attributes
        assert f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.arguments" in tool_instrumented_span.attributes
        
        # Verify the specific tool call values
        assert tool_instrumented_span.attributes[f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.id"] == "call_EKUsxI7LNqe2beBJlNAGNsd3"
        assert tool_instrumented_span.attributes[f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.name"] == "get_weather"
        assert "San Francisco" in tool_instrumented_span.attributes[f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.arguments"]

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
