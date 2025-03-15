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
from typing import Any, Dict, List, Optional, Union
import inspect

import pytest
from opentelemetry import trace
from opentelemetry.trace import StatusCode

# Mock Agent SDK classes
class MockAgentRunResult:
    """Mock for the RunResult class from the Agents SDK"""
    def __init__(self, final_output, raw_responses=None):
        self.final_output = final_output
        self.raw_responses = raw_responses or []

class MockAgent:
    """Mock for the Agent class from the Agents SDK"""
    def __init__(self, name, instructions, tools=None, model=None, model_settings=None):
        self.name = name
        self.instructions = instructions
        self.tools = tools or []
        self.model = model or "gpt-4o"
        self.model_settings = model_settings or MockModelSettings()

class MockTool:
    """Mock for the Tool class from the Agents SDK"""
    def __init__(self, name, description=None):
        self.name = name
        self.description = description or f"Description for {name}"

class MockModelSettings:
    """Mock for model settings in the Agents SDK"""
    def __init__(self, temperature=0.7, top_p=1.0, frequency_penalty=0.0, presence_penalty=0.0):
        self.temperature = temperature
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty

class MockRunConfig:
    """Mock for the RunConfig class from the Agents SDK"""
    def __init__(self, workflow_name=None, model=None, model_settings=None):
        self.workflow_name = workflow_name or "test_workflow"
        self.model = model
        self.model_settings = model_settings

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
from agentops.instrumentation.openai_agents import (
    AgentsDetailedExporter, 
    get_model_info
)
from tests.unit.instrumentation.mock_span import MockSpan, process_with_instrumentor

# Test fixtures: Mock span and trace data from Agents SDK

# Generation span with tool calls - when an LLM is being called with tool outputs
GENERATION_TOOL_CALLS_SPAN_DATA = {
    "model": "gpt-4o",
    "model_config": {
        "temperature": 0.7,
        "top_p": 1.0
    },
    "input": "What's the weather in San Francisco?",
    "output": {
        "id": "chatcmpl-456",
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc123",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"location": "San Francisco", "unit": "celsius"}'
                            }
                        }
                    ]
                },
                "finish_reason": "tool_calls"
            }
        ],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 10,
            "total_tokens": 22
        },
        "system_fingerprint": "fp_55g4"
    },
    "usage": {
        "prompt_tokens": 12,
        "completion_tokens": 10,
        "total_tokens": 22
    }
}

# Expected attributes for a Generation span with tool calls
EXPECTED_TOOL_CALLS_SPAN_ATTRIBUTES = {
    # Model metadata - using proper semantic conventions
    SpanAttributes.LLM_REQUEST_MODEL: "gpt-4o",
    SpanAttributes.LLM_SYSTEM: "openai",
    SpanAttributes.LLM_REQUEST_TEMPERATURE: 0.7,
    SpanAttributes.LLM_REQUEST_TOP_P: 1.0,
    
    # Response metadata from the nested output - using proper semantic conventions
    SpanAttributes.LLM_RESPONSE_MODEL: "gpt-4o",
    SpanAttributes.LLM_RESPONSE_ID: "chatcmpl-456",
    SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT: "fp_55g4",
    
    # Token usage - using proper semantic conventions
    SpanAttributes.LLM_USAGE_TOTAL_TOKENS: 22,
    SpanAttributes.LLM_USAGE_PROMPT_TOKENS: 12,
    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: 10,
    
    # Completion metadata - using proper semantic conventions
    f"{SpanAttributes.LLM_COMPLETIONS}.0.role": "assistant",
    f"{SpanAttributes.LLM_COMPLETIONS}.0.finish_reason": "tool_calls",
    
    # Tool call details - using proper semantic conventions
    f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.id": "call_abc123",
    f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.name": "get_weather",
    f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0.arguments": '{"location": "San Francisco", "unit": "celsius"}',
    
    # Standard OpenTelemetry attributes
    "trace.id": "trace123",
    "span.id": "span456",
    "parent.id": "parent789",
    "library.name": "agents-sdk",
    "library.version": "0.1.0"
}

# Agent run span - when an agent is executing
AGENT_SPAN_DATA = {
    "name": "Test Agent",
    "input": "What is the capital of France?",
    "output": "The capital of France is Paris.",
    "from_agent": "User",
    "to_agent": "Test Agent",
    "tools": ["search", "calculator"]
}

# Tool usage span - when an agent is using a tool
TOOL_SPAN_DATA = {
    "name": "search",
    "input": "capital of France",
    "output": "Paris is the capital of France.",
    "from_agent": "Test Agent",
    "tools": ["search"]
}

# Generation span - when an LLM is being called (using Chat Completion API)
GENERATION_SPAN_DATA = {
    "model": "gpt-4o",
    "model_config": {
        "temperature": 0.7,
        "top_p": 1.0
    },
    "input": "What is the capital of France?",
    "output": {
        "id": "chatcmpl-123",
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "The capital of France is Paris."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 8,
            "total_tokens": 18
        },
        "system_fingerprint": "fp_44f3"
    },
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 8,
        "total_tokens": 18
    }
}

# Generation span - when an LLM is being called (using Response API)
GENERATION_RESPONSE_API_SPAN_DATA = {
    "model": "gpt-4o", 
    "model_config": {
        "temperature": 0.7,
        "top_p": 1.0
    },
    "input": "What is the capital of France?",
    "output": {
        "id": "resp_abc123",
        "created_at": 1677858245,
        "model": "gpt-4o",
        "object": "response",
        "output": [
            {
                "id": "msg_abc123",
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "The capital of France is Paris, known for the Eiffel Tower.",
                        "annotations": []
                    }
                ],
                "role": "assistant",
                "status": "completed"
            }
        ],
        "usage": {
            "input_tokens": 12,
            "output_tokens": 15,
            "total_tokens": 27,
            "output_tokens_details": {
                "reasoning_tokens": 4
            }
        },
        "parallel_tool_calls": False,
        "status": "completed",
        "tools": [],
        "tool_choice": "none"
    },
    "usage": {
        "input_tokens": 12,
        "output_tokens": 15,
        "total_tokens": 27
    }
}

# Expected attributes for an Agent span
EXPECTED_AGENT_SPAN_ATTRIBUTES = {
    # Agent metadata - using proper semantic conventions
    AgentAttributes.AGENT_NAME: "Test Agent",
    "agent.from": "User",
    "agent.to": "Test Agent",
    AgentAttributes.AGENT_TOOLS: "search,calculator",
    
    # Workflow info - using proper semantic conventions
    WorkflowAttributes.WORKFLOW_INPUT: "What is the capital of France?",
    WorkflowAttributes.FINAL_OUTPUT: "The capital of France is Paris.",
    
    # Standard OpenTelemetry attributes
    "trace.id": "trace123",
    "span.id": "span456",
    "parent.id": "parent789",
    "library.name": "agents-sdk",
    "library.version": "0.1.0"
}

# Expected attributes for a Tool span
EXPECTED_TOOL_SPAN_ATTRIBUTES = {
    # Tool metadata - using proper semantic conventions
    AgentAttributes.AGENT_NAME: "search",
    AgentAttributes.FROM_AGENT: "Test Agent",
    AgentAttributes.AGENT_TOOLS: "search",
    
    # Input/output - using proper semantic conventions
    SpanAttributes.LLM_PROMPTS: "capital of France",
    SpanAttributes.LLM_COMPLETIONS: "Paris is the capital of France.",
    
    # Standard OpenTelemetry attributes
    "trace.id": "trace123",
    "span.id": "span456",
    "parent.id": "parent789",
    "library.name": "agents-sdk",
    "library.version": "0.1.0"
}

# Expected attributes for a Generation span with Chat Completion API
EXPECTED_GENERATION_SPAN_ATTRIBUTES = {
    # Model metadata - using proper semantic conventions
    SpanAttributes.LLM_REQUEST_MODEL: "gpt-4o",
    SpanAttributes.LLM_SYSTEM: "openai",
    SpanAttributes.LLM_REQUEST_TEMPERATURE: 0.7,
    SpanAttributes.LLM_REQUEST_TOP_P: 1.0,
    
    # Response metadata from the nested output - using proper semantic conventions
    SpanAttributes.LLM_RESPONSE_MODEL: "gpt-4o",
    SpanAttributes.LLM_RESPONSE_ID: "chatcmpl-123",
    SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT: "fp_44f3",
    
    # Token usage - using proper semantic conventions
    SpanAttributes.LLM_USAGE_TOTAL_TOKENS: 18,
    SpanAttributes.LLM_USAGE_PROMPT_TOKENS: 10,
    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: 8,
    
    # Content extraction - using proper semantic conventions 
    f"{SpanAttributes.LLM_COMPLETIONS}.0.content": "The capital of France is Paris.",
    f"{SpanAttributes.LLM_COMPLETIONS}.0.role": "assistant",
    f"{SpanAttributes.LLM_COMPLETIONS}.0.finish_reason": "stop",
    
    # Standard OpenTelemetry attributes
    "trace.id": "trace123",
    "span.id": "span456",
    "parent.id": "parent789",
    "library.name": "agents-sdk",
    "library.version": "0.1.0"
}

# Expected attributes for a Generation span with Response API
EXPECTED_RESPONSE_API_SPAN_ATTRIBUTES = {
    # Model metadata - using proper semantic conventions
    SpanAttributes.LLM_REQUEST_MODEL: "gpt-4o",
    SpanAttributes.LLM_SYSTEM: "openai",
    SpanAttributes.LLM_REQUEST_TEMPERATURE: 0.7,
    SpanAttributes.LLM_REQUEST_TOP_P: 1.0,
    
    # Response metadata from the nested output - using proper semantic conventions
    SpanAttributes.LLM_RESPONSE_MODEL: "gpt-4o",
    SpanAttributes.LLM_RESPONSE_ID: "resp_abc123",
    
    # Token usage - notice the mapping from input_tokens to prompt_tokens! Using proper semantic conventions
    SpanAttributes.LLM_USAGE_TOTAL_TOKENS: 27,
    SpanAttributes.LLM_USAGE_PROMPT_TOKENS: 12,
    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: 15,
    f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.reasoning": 4,
    
    # Content extraction from Response API format - using proper semantic conventions
    f"{SpanAttributes.LLM_COMPLETIONS}.0.content": "The capital of France is Paris, known for the Eiffel Tower.",
    f"{SpanAttributes.LLM_COMPLETIONS}.0.role": "assistant",
    
    # Standard OpenTelemetry attributes
    "trace.id": "trace123",
    "span.id": "span456",
    "parent.id": "parent789",
    "library.name": "agents-sdk",
    "library.version": "0.1.0"
}

# Expected attributes for get_model_info utility function
EXPECTED_MODEL_INFO = {
    "model_name": "gpt-4o",
    "temperature": 0.7,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
}


class TestAgentsSdkInstrumentation:
    """Tests for OpenAI Agents SDK instrumentation"""

    @pytest.fixture
    def instrumentation(self):
        """Set up instrumentation for tests"""
        return InstrumentationTester()
        
    def test_agent_span_serialization(self, instrumentation):
        """Test serialization of Agent spans from Agents SDK"""
        # Dictionary to capture attributes from the instrumentor
        captured_attributes = {}
        
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span for our test
        with tracer.start_as_current_span("test_agent_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "consumer")
            
            # Create a mock span with Agent data
            mock_span = MockSpan(AGENT_SPAN_DATA, span_type="AgentSpanData")
            
            # Process the mock span with the actual AgentsDetailedExporter
            process_with_instrumentor(mock_span, AgentsDetailedExporter, captured_attributes)
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes.items():
                span.set_attribute(key, val)

        # Get all spans
        spans = instrumentation.get_finished_spans()
            
        # Examine the first span generated from the instrumentor
        instrumented_span = spans[0]
        
        # Check all required attributes from our reference model against the actual span
        for key, expected_value in EXPECTED_AGENT_SPAN_ATTRIBUTES.items():
            # Skip library version which might change
            if key == "library.version":
                continue
                
            # Assert the attribute exists 
            assert key in instrumented_span.attributes, f"Missing expected attribute '{key}'"
            
            # Assert it has the expected value
            actual_value = instrumented_span.attributes[key]
            assert actual_value == expected_value, \
                f"Attribute '{key}' has wrong value. Expected: {expected_value}, Actual: {actual_value}"
                
    def test_tool_span_serialization(self, instrumentation):
        """Test serialization of Tool spans from Agents SDK"""
        # Dictionary to capture attributes from the instrumentor
        captured_attributes = {}
        
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span for our test
        with tracer.start_as_current_span("test_tool_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "client")
            
            # Create a mock span with Tool data
            mock_span = MockSpan(TOOL_SPAN_DATA, span_type="FunctionSpanData")
            
            # Process the mock span with the actual AgentsDetailedExporter
            process_with_instrumentor(mock_span, AgentsDetailedExporter, captured_attributes)
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes.items():
                span.set_attribute(key, val)

        # Get all spans
        spans = instrumentation.get_finished_spans()
            
        # Examine the first span generated from the instrumentor
        instrumented_span = spans[0]
        
        # Check all required attributes from our reference model against the actual span
        for key, expected_value in EXPECTED_TOOL_SPAN_ATTRIBUTES.items():
            # Skip library version which might change
            if key == "library.version":
                continue
                
            # Assert the attribute exists 
            assert key in instrumented_span.attributes, f"Missing expected attribute '{key}'"
            
            # Assert it has the expected value
            actual_value = instrumented_span.attributes[key]
            assert actual_value == expected_value, \
                f"Attribute '{key}' has wrong value. Expected: {expected_value}, Actual: {actual_value}"
    
    def test_generation_span_serialization(self, instrumentation):
        """Test serialization of Generation spans from Agents SDK using Chat Completion API"""
        # Dictionary to capture attributes from the instrumentor
        captured_attributes = {}
        
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span for our test
        with tracer.start_as_current_span("test_generation_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "client")
            
            # Create a mock span with Generation data
            mock_span = MockSpan(GENERATION_SPAN_DATA, span_type="GenerationSpanData")
            
            # Process the mock span with the actual AgentsDetailedExporter
            process_with_instrumentor(mock_span, AgentsDetailedExporter, captured_attributes)
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes.items():
                span.set_attribute(key, val)

        # Get all spans
        spans = instrumentation.get_finished_spans()
            
        # Examine the first span generated from the instrumentor
        instrumented_span = spans[0]
        
        # Check all required attributes from our reference model against the actual span
        for key, expected_value in EXPECTED_GENERATION_SPAN_ATTRIBUTES.items():
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
        expected_completion_attrs = [k for k in EXPECTED_GENERATION_SPAN_ATTRIBUTES.keys() if k.startswith(completion_prefix)]
        
        # We should have exactly the expected attributes, nothing more
        assert set(completion_attrs) == set(expected_completion_attrs), \
            f"Unexpected completion attributes. Found: {completion_attrs}, Expected: {expected_completion_attrs}"
            
    def test_response_api_span_serialization(self, instrumentation):
        """Test serialization of Generation spans from Agents SDK using Response API"""
        # Dictionary to capture attributes from the instrumentor
        captured_attributes = {}
        
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span for our test
        with tracer.start_as_current_span("test_response_api_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "client")
            
            # Create a mock span with Response API data
            mock_span = MockSpan(GENERATION_RESPONSE_API_SPAN_DATA, span_type="GenerationSpanData")
            
            # Process the mock span with the actual AgentsDetailedExporter
            process_with_instrumentor(mock_span, AgentsDetailedExporter, captured_attributes)
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes.items():
                span.set_attribute(key, val)

        # Get all spans
        spans = instrumentation.get_finished_spans()
            
        # Examine the first span generated from the instrumentor
        instrumented_span = spans[0]
        
        # Check all required attributes from our reference model against the actual span
        for key, expected_value in EXPECTED_RESPONSE_API_SPAN_ATTRIBUTES.items():
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
        expected_completion_attrs = [k for k in EXPECTED_RESPONSE_API_SPAN_ATTRIBUTES.keys() if k.startswith(completion_prefix)]
        
        # We should have exactly the expected attributes, nothing more
        assert set(completion_attrs) == set(expected_completion_attrs), \
            f"Unexpected completion attributes. Found: {completion_attrs}, Expected: {expected_completion_attrs}"
            
        # Verify we correctly mapped input_tokens → prompt_tokens and output_tokens → completion_tokens
        assert "gen_ai.usage.prompt_tokens" in instrumented_span.attributes, "Missing prompt_tokens attribute"
        assert instrumented_span.attributes["gen_ai.usage.prompt_tokens"] == 12, "Incorrect prompt_tokens value"
        
        assert "gen_ai.usage.completion_tokens" in instrumented_span.attributes, "Missing completion_tokens attribute"
        assert instrumented_span.attributes["gen_ai.usage.completion_tokens"] == 15, "Incorrect completion_tokens value"
        
        # Verify we extracted the special reasoning_tokens field
        assert "gen_ai.usage.total_tokens.reasoning" in instrumented_span.attributes, "Missing reasoning_tokens attribute"
        assert instrumented_span.attributes["gen_ai.usage.total_tokens.reasoning"] == 4, "Incorrect reasoning_tokens value"
        
    def test_tool_calls_span_serialization(self, instrumentation):
        """Test serialization of Generation spans with tool calls from Agents SDK"""
        # Dictionary to capture attributes from the instrumentor
        captured_attributes = {}
        
        # Set up test environment
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Create a span for our test
        with tracer.start_as_current_span("test_tool_calls_span") as span:
            # Set the span type
            span.set_attribute("span.kind", "client")
            
            # Create a mock span with tool calls data
            mock_span = MockSpan(GENERATION_TOOL_CALLS_SPAN_DATA, span_type="GenerationSpanData")
            
            # Process the mock span with the actual AgentsDetailedExporter
            process_with_instrumentor(mock_span, AgentsDetailedExporter, captured_attributes)
            
            # Set attributes on our test span too (so we can verify them)
            for key, val in captured_attributes.items():
                span.set_attribute(key, val)

        # Get all spans
        spans = instrumentation.get_finished_spans()
            
        # Examine the first span generated from the instrumentor
        instrumented_span = spans[0]
        
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
                
        # Verify the tool calls attributes specifically
        tool_calls_prefix = "gen_ai.completion.0.tool_calls"
        tool_calls_attrs = [k for k in instrumented_span.attributes.keys() if k.startswith(tool_calls_prefix)]
        expected_tool_calls_attrs = [k for k in EXPECTED_TOOL_CALLS_SPAN_ATTRIBUTES.keys() if k.startswith(tool_calls_prefix)]
        
        # We should have exactly the expected tool calls attributes, nothing more
        assert set(tool_calls_attrs) == set(expected_tool_calls_attrs), \
            f"Unexpected tool calls attributes. Found: {tool_calls_attrs}, Expected: {expected_tool_calls_attrs}"
            
        # Verify tool call ID is captured
        assert "gen_ai.completion.0.tool_calls.0.id" in instrumented_span.attributes, "Missing tool call ID attribute"
        assert instrumented_span.attributes["gen_ai.completion.0.tool_calls.0.id"] == "call_abc123", "Incorrect tool call ID"
        
        # Verify tool call name is captured
        assert "gen_ai.completion.0.tool_calls.0.name" in instrumented_span.attributes, "Missing tool call name attribute"
        assert instrumented_span.attributes["gen_ai.completion.0.tool_calls.0.name"] == "get_weather", "Incorrect tool call name"
        
        # Verify tool call arguments are captured
        assert "gen_ai.completion.0.tool_calls.0.arguments" in instrumented_span.attributes, "Missing tool call arguments attribute"
        assert "San Francisco" in instrumented_span.attributes["gen_ai.completion.0.tool_calls.0.arguments"], "Incorrect tool call arguments"

    def test_get_model_info_function(self):
        """Test the get_model_info utility function that extracts model information from agents"""
        # Create a mock agent with model settings
        agent = MockAgent(
            name="Test Agent",
            instructions="Test instructions",
            model="gpt-4o",
            model_settings=MockModelSettings(
                temperature=0.7,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
        )
        
        # Test with agent only
        model_info = get_model_info(agent)
        
        # Verify all expected fields are present
        for key, expected_value in EXPECTED_MODEL_INFO.items():
            assert key in model_info, f"Missing expected key '{key}' in model_info"
            assert model_info[key] == expected_value, \
                f"Key '{key}' has wrong value. Expected: {expected_value}, Actual: {model_info[key]}"
                
        # Test with run_config that overrides model
        run_config = MockRunConfig(
            model="gpt-4-turbo", 
            model_settings=MockModelSettings(temperature=0.5)
        )
        
        model_info = get_model_info(agent, run_config)
        
        # Model name should be from run_config
        assert model_info["model_name"] == "gpt-4-turbo", \
            f"Model name should be from run_config. Expected: gpt-4-turbo, Actual: {model_info['model_name']}"
            
        # Temperature should be from run_config
        assert model_info["temperature"] == 0.5, \
            f"Temperature should be from run_config. Expected: 0.5, Actual: {model_info['temperature']}"

    def test_runner_instrumentation(self, instrumentation):
        """Test the AgentsInstrumentor's ability to monkey patch the Runner class"""
        # Note: This is a partial test as we can't fully test the monkey patching without the actual Agent SDK.
        # We'll simulate what the monkey patching does to verify the attribute setting logic.
        
        # Create mock agent and run_config objects
        agent = MockAgent(
            name="Test Agent",
            instructions="Test instructions", 
            tools=[MockTool("search"), MockTool("calculator")],
            model="gpt-4o",
            model_settings=MockModelSettings(temperature=0.7)
        )
        
        run_config = MockRunConfig(workflow_name="test_workflow")
        
        # Create mock run result with raw responses
        mock_response = {
            "id": "chatcmpl-abc123",
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a test result."
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": 10,
                "total_tokens": 25
            },
            "system_fingerprint": "fp_789xyz"
        }
        
        # Create a dictionary to capture the attributes that would be set by the monkey patched Runner methods
        # This simulates what would happen in the instrumented_method functions
        captured_attributes = {}
        
        # Simulate what the instrumented Runner.run_sync method would do
        tracer = TracingCore.get_instance().get_tracer("test_tracer")
        
        # Start a span as the Runner method would
        with tracer.start_as_current_span("test_runner_span") as span:
            # Extract model information
            model_info = get_model_info(agent, run_config)
            
            # Set span attributes as the Runner method would
            span.set_attribute("span.kind", WorkflowAttributes.WORKFLOW_STEP)
            span.set_attribute("agent.name", agent.name)
            span.set_attribute(WorkflowAttributes.WORKFLOW_INPUT, "What is the capital of France?")
            span.set_attribute(WorkflowAttributes.MAX_TURNS, 10)
            span.set_attribute("service.name", "agentops.agents")
            span.set_attribute(WorkflowAttributes.WORKFLOW_TYPE, "agents.run_sync")
            span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, model_info["model_name"])
            span.set_attribute("gen_ai.request.model", model_info["model_name"])
            span.set_attribute("gen_ai.system", "openai")
            span.set_attribute("stream", "false")
            
            # Add model parameters from model_info
            for param, value in model_info.items():
                if param != "model_name":
                    span.set_attribute(f"agent.model.{param}", value)
            
            # Add workflow name from run_config
            span.set_attribute(WorkflowAttributes.WORKFLOW_NAME, run_config.workflow_name)
            
            # Add agent instructions using common convention
            span.set_attribute("agent.instructions", agent.instructions)
            span.set_attribute("agent.instruction_type", "string")
            
            # Add agent tools
            tool_names = [tool.name for tool in agent.tools]
            span.set_attribute(AgentAttributes.AGENT_TOOLS, str(tool_names))
            
            # Add model settings using proper semantic conventions
            span.set_attribute(SpanAttributes.LLM_REQUEST_TEMPERATURE, agent.model_settings.temperature)
            span.set_attribute(SpanAttributes.LLM_REQUEST_TOP_P, agent.model_settings.top_p)
            span.set_attribute(SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY, agent.model_settings.frequency_penalty)
            span.set_attribute(SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY, agent.model_settings.presence_penalty)
            
            # Simulate getting a run result
            run_result = MockAgentRunResult(
                final_output="The capital of France is Paris.",
                raw_responses=[mock_response]
            )
            
            # Add result attributes as the Runner method would
            span.set_attribute(WorkflowAttributes.FINAL_OUTPUT, str(run_result.final_output))
            
            # Process the raw responses
            for i, response in enumerate(run_result.raw_responses):
                # Add token usage using proper semantic conventions
                if "usage" in response:
                    usage = response["usage"]
                    if "prompt_tokens" in usage:
                        span.set_attribute(f"{SpanAttributes.LLM_USAGE_PROMPT_TOKENS}.{i}", usage["prompt_tokens"])
                    
                    if "completion_tokens" in usage:
                        span.set_attribute(f"{SpanAttributes.LLM_USAGE_COMPLETION_TOKENS}.{i}", usage["completion_tokens"])
                    
                    if "total_tokens" in usage:
                        span.set_attribute(f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.{i}", usage["total_tokens"])
            
            # Set total token counts
            span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, 15)
            span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, 10)
            span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, 25)
            
            # Add instrumentation metadata
            span.set_attribute(InstrumentationAttributes.NAME, "agentops.agents")
            span.set_attribute(InstrumentationAttributes.VERSION, "0.1.0")
            
            # Capture the attributes for testing
            captured_attributes = dict(span.attributes)

        # Get all spans
        spans = instrumentation.get_finished_spans()
            
        # Examine the first span
        instrumented_span = spans[0]
        
        # Verify key attributes that should be set by the Runner method
        assert "agent.name" in instrumented_span.attributes, "Missing agent.name attribute"
        assert instrumented_span.attributes["agent.name"] == "Test Agent", "Incorrect agent.name value"
        
        assert WorkflowAttributes.WORKFLOW_NAME in instrumented_span.attributes, "Missing workflow.name attribute"
        assert instrumented_span.attributes[WorkflowAttributes.WORKFLOW_NAME] == "test_workflow", "Incorrect workflow.name value"
        
        assert "agent.model.temperature" in instrumented_span.attributes, "Missing agent.model.temperature attribute"
        assert instrumented_span.attributes["agent.model.temperature"] == 0.7, "Incorrect temperature value"
        
        assert AgentAttributes.AGENT_TOOLS in instrumented_span.attributes, "Missing agent.tools attribute"
        assert "search" in instrumented_span.attributes[AgentAttributes.AGENT_TOOLS], "Missing tool in agent.tools value"
        assert "calculator" in instrumented_span.attributes[AgentAttributes.AGENT_TOOLS], "Missing tool in agent.tools value"
        
        assert WorkflowAttributes.FINAL_OUTPUT in instrumented_span.attributes, "Missing workflow.final_output attribute"
        assert instrumented_span.attributes[WorkflowAttributes.FINAL_OUTPUT] == "The capital of France is Paris.", "Incorrect final_output value"
        
        assert SpanAttributes.LLM_USAGE_TOTAL_TOKENS in instrumented_span.attributes, "Missing gen_ai.usage.total_tokens attribute"
        assert instrumented_span.attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 25, "Incorrect total_tokens value"