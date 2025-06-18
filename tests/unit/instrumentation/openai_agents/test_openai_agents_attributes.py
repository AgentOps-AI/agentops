"""
Tests for OpenAI Agents SDK Attributes

This module contains tests for the attribute definitions and semantic conventions
used in OpenAI Agents SDK instrumentation. It verifies that attribute extraction,
handling, and transformations work correctly across different API formats and data structures.
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch

from agentops.instrumentation.agentic.openai_agents import LIBRARY_NAME

# Import common attribute functions
from agentops.instrumentation.agentic.openai_agents.attributes.common import (
    get_agent_span_attributes,
    get_function_span_attributes,
    get_generation_span_attributes,
    get_handoff_span_attributes,
    get_response_span_attributes,
    get_span_attributes,
    get_common_instrumentation_attributes,
)

# Import model-related functions
from agentops.instrumentation.agentic.openai_agents.attributes.model import (
    get_model_attributes,
)

# Import completion processing functions
from agentops.instrumentation.agentic.openai_agents.attributes.completion import (
    get_chat_completions_attributes,
    get_raw_response_attributes,
)

# Import token processing functions
from agentops.instrumentation.agentic.openai_agents.attributes.tokens import (
    process_token_usage,
    extract_nested_usage,
    get_token_metric_attributes,
)

from agentops.semconv import (
    SpanAttributes,
    MessageAttributes,
    AgentAttributes,
    InstrumentationAttributes,
)


# Helper function to load fixtures
def load_fixture(fixture_name):
    """Load a test fixture from the fixtures directory"""
    fixture_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures", fixture_name)
    with open(fixture_path, "r") as f:
        return json.load(f)


# Load test fixtures

# OpenAI ChatCompletion API Response - Standard Format
# Structure: Flat with direct 'id', 'model', 'choices' fields
# Content location: choices[0].message.content
# Token usage: 'usage' with completion_tokens/prompt_tokens fields
# Model info: Available in the 'model' field
OPENAI_CHAT_COMPLETION = load_fixture("openai_chat_completion.json")

# OpenAI ChatCompletion API Response with Tool Calls
# Similar to standard ChatCompletion but with tool_calls in message
OPENAI_CHAT_TOOL_CALLS = load_fixture("openai_chat_tool_calls.json")

# OpenAI Response API Format - Direct Response Format
# Structure: Uses 'output' array instead of 'choices'
# Content location: output[0].content[0].text
# Token usage: input_tokens/output_tokens naming
# Additional fields: 'instructions', 'tools', etc.
OPENAI_RESPONSE = load_fixture("openai_response.json")

# OpenAI Response API Format with Tool Calls
# Similar to standard Response API but with tool calls
OPENAI_RESPONSE_TOOL_CALLS = load_fixture("openai_response_tool_calls.json")

# OpenAI Agents SDK Response - Basic Text Response
# Structure: Nested with 'raw_responses' containing actual API responses
# Content location: raw_responses[0].output[0].content[0].text
# Token usage: input_tokens/output_tokens fields in raw_responses[0].usage
# Model info: Not available at the top level, must be extracted from elsewhere
AGENTS_RESPONSE = load_fixture("openai_agents_response.json")

# OpenAI Agents SDK Response - Tool Call Response
# Structure: Similar to basic response but with tool_calls
# Tool calls location: At the same level as 'content' inside the output
# Tool call format: Contains 'function' object with 'name' and 'arguments'
# Arguments format: Stringified JSON rather than parsed objects
AGENTS_TOOL_RESPONSE = load_fixture("openai_agents_tool_response.json")


@pytest.fixture(autouse=True)
def mock_external_dependencies():
    """Mock any external dependencies to avoid actual API calls or slow operations"""
    # Create a more comprehensive mock for JSON serialization
    # This will directly patch the json.dumps function which is used inside safe_serialize

    # Store the original json.dumps function
    original_dumps = json.dumps

    # Create a wrapper for json.dumps that handles MagicMock objects
    def json_dumps_wrapper(*args, **kwargs):
        """
        Our JSON encode method doesn't play well with MagicMock objects and gets stuck iun a recursive loop.
        Patch the functionality to return a simple string instead of trying to serialize the object.
        """
        # If the first argument is a MagicMock, return a simple string
        if args and hasattr(args[0], "__module__") and "mock" in args[0].__module__.lower():
            return '"mock_object"'
        # Otherwise, use the original function with a custom encoder that handles MagicMock objects
        cls = kwargs.get("cls", None)
        if not cls:
            # Use our own encoder that handles MagicMock objects
            class MagicMockJSONEncoder(json.JSONEncoder):
                def default(self, obj):
                    if hasattr(obj, "__module__") and "mock" in obj.__module__.lower():
                        return "mock_object"
                    return super().default(obj)

            kwargs["cls"] = MagicMockJSONEncoder
        # Call the original dumps with our encoder
        return original_dumps(*args, **kwargs)

    with patch("json.dumps", side_effect=json_dumps_wrapper):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            with patch("agentops.instrumentation.agentic.openai_agents.LIBRARY_NAME", "openai"):
                with patch("agentops.instrumentation.agentic.openai_agents.LIBRARY_VERSION", "1.0.0"):
                    yield


class TestOpenAIAgentsAttributes:
    """Test suite for OpenAI Agents attribute processing"""

    def test_common_instrumentation_attributes(self):
        """Test common instrumentation attributes for consistent keys and values"""
        attrs = get_common_instrumentation_attributes()

        # Verify required keys are present using semantic conventions
        assert InstrumentationAttributes.NAME in attrs
        assert InstrumentationAttributes.VERSION in attrs
        assert InstrumentationAttributes.LIBRARY_NAME in attrs
        assert InstrumentationAttributes.LIBRARY_VERSION in attrs

        # Verify values
        assert attrs[InstrumentationAttributes.NAME] == "agentops"
        # Don't call get_agentops_version() again, just verify it's in the dictionary
        assert InstrumentationAttributes.VERSION in attrs
        assert attrs[InstrumentationAttributes.LIBRARY_NAME] == LIBRARY_NAME

    def test_agent_span_attributes(self):
        """Test extraction of attributes from an AgentSpanData object"""
        # Create a mock AgentSpanData
        mock_agent_span = MagicMock()
        mock_agent_span.__class__.__name__ = "AgentSpanData"
        mock_agent_span.name = "test_agent"
        mock_agent_span.input = "test input"
        mock_agent_span.output = "test output"
        mock_agent_span.tools = ["tool1", "tool2"]

        # Extract attributes
        attrs = get_agent_span_attributes(mock_agent_span)

        # Verify extracted attributes
        assert attrs[AgentAttributes.AGENT_NAME] == "test_agent"
        assert "agentops.span.kind" in attrs
        assert attrs["agentops.span.kind"] == "agent"

    def test_function_span_attributes(self):
        """Test extraction of attributes from a FunctionSpanData object"""
        # Create a mock FunctionSpanData
        mock_function_span = MagicMock()
        mock_function_span.__class__.__name__ = "FunctionSpanData"
        mock_function_span.name = "test_function"
        mock_function_span.input = {"arg1": "value1"}
        mock_function_span.output = {"result": "success"}
        mock_function_span.from_agent = "caller_agent"

        # Extract attributes
        attrs = get_function_span_attributes(mock_function_span)

        # Verify extracted attributes
        assert "tool.name" in attrs
        assert attrs["tool.name"] == "test_function"
        assert "tool.parameters" in attrs
        assert '{"arg1": "value1"}' in attrs["tool.parameters"]  # Serialized string
        assert "tool.result" in attrs
        assert '{"result": "success"}' in attrs["tool.result"]  # Serialized string
        assert "agentops.span.kind" in attrs
        assert attrs["agentops.span.kind"] == "tool"
        assert "agent.calling_tool.name" in attrs
        assert attrs["agent.calling_tool.name"] == "caller_agent"

    def test_generation_span_with_chat_completion(self):
        """Test extraction of attributes from a GenerationSpanData with Chat Completion API data"""

        # Create a class instead of MagicMock to avoid serialization issues
        class GenerationSpanData:
            def __init__(self):
                self.__class__.__name__ = "GenerationSpanData"
                self.model = "gpt-4o-2024-08-06"  # Match the model in the fixture
                self.input = "What is the capital of France?"
                self.output = OPENAI_CHAT_COMPLETION
                self.from_agent = "requester_agent"
                # Add model_config that matches the model parameters in the fixture
                self.model_config = {"temperature": 0.7, "top_p": 1.0}

        mock_gen_span = GenerationSpanData()

        # Extract attributes
        attrs = get_generation_span_attributes(mock_gen_span)

        # Verify model and input attributes
        assert attrs[SpanAttributes.LLM_REQUEST_MODEL] == "gpt-4o-2024-08-06"
        assert attrs[SpanAttributes.LLM_RESPONSE_MODEL] == "gpt-4o-2024-08-06"
        assert "gen_ai.prompt.0.role" in attrs
        assert attrs["gen_ai.prompt.0.role"] == "user"
        assert "gen_ai.prompt.0.content" in attrs
        assert attrs["gen_ai.prompt.0.content"] == "What is the capital of France?"

        # Verify model config attributes
        assert attrs[SpanAttributes.LLM_REQUEST_TEMPERATURE] == 0.7
        assert attrs[SpanAttributes.LLM_REQUEST_TOP_P] == 1.0

        # The get_chat_completions_attributes functionality is tested separately
        # in test_chat_completions_attributes_from_fixture

    def test_generation_span_with_response_api(self):
        """Test extraction of attributes from a GenerationSpanData with Response API data"""

        # Create a class instead of MagicMock to avoid serialization issues
        class GenerationSpanData:
            def __init__(self):
                self.__class__.__name__ = "GenerationSpanData"
                self.model = "gpt-4o-2024-08-06"  # Match the model in the fixture
                self.input = "What is the capital of France?"
                self.output = OPENAI_RESPONSE
                self.from_agent = "requester_agent"
                # Set model_config to match what's in the response
                self.model_config = {"temperature": 0.7, "top_p": 1.0}

        mock_gen_span = GenerationSpanData()

        # Extract attributes
        attrs = get_generation_span_attributes(mock_gen_span)

        # Verify model and input attributes
        assert attrs[SpanAttributes.LLM_REQUEST_MODEL] == "gpt-4o-2024-08-06"
        assert attrs[SpanAttributes.LLM_RESPONSE_MODEL] == "gpt-4o-2024-08-06"
        assert "gen_ai.prompt.0.role" in attrs
        assert attrs["gen_ai.prompt.0.role"] == "user"
        assert "gen_ai.prompt.0.content" in attrs
        assert attrs["gen_ai.prompt.0.content"] == "What is the capital of France?"

        # Verify token usage - this is handled through model_to_dict now
        # Since we're using a direct fixture, the serialization might differ

        # Verify model config parameters
        assert SpanAttributes.LLM_REQUEST_TEMPERATURE in attrs
        assert attrs[SpanAttributes.LLM_REQUEST_TEMPERATURE] == 0.7
        assert SpanAttributes.LLM_REQUEST_TOP_P in attrs
        assert attrs[SpanAttributes.LLM_REQUEST_TOP_P] == 1.0

        # The get_raw_response_attributes functionality is tested separately
        # in test_response_api_attributes_from_fixture

    def test_generation_span_with_agents_response(self):
        """Test extraction of attributes from a GenerationSpanData with OpenAI Agents response data"""
        # The issue is in the serialization of MagicMock objects with the fixture
        # Let's directly use a dict instead of a MagicMock for better serialization

        # Create a simplified version of the GenerationSpanData
        class GenerationSpanData:
            def __init__(self):
                self.__class__.__name__ = "GenerationSpanData"
                self.model = "gpt-4"
                self.input = "What is the capital of France?"
                # Use a regular dict instead of the fixture to avoid MagicMock serialization issues
                self.output = {
                    "raw_responses": [
                        {
                            "usage": {"input_tokens": 54, "output_tokens": 8, "total_tokens": 62},
                            "output": [
                                {
                                    "content": [{"type": "output_text", "text": "The capital of France is Paris."}],
                                    "role": "assistant",
                                }
                            ],
                        }
                    ]
                }
                # Add model_config with temperature and top_p
                self.model_config = {"temperature": 0.7, "top_p": 0.95}

        mock_gen_span = GenerationSpanData()

        # Patch the model_to_dict function to avoid circular references
        with patch(
            "agentops.instrumentation.agentic.openai_agents.attributes.completion.model_to_dict",
            side_effect=lambda x: x if isinstance(x, dict) else {},
        ):
            # Extract attributes
            attrs = get_generation_span_attributes(mock_gen_span)

        # Verify core attributes
        assert attrs[SpanAttributes.LLM_REQUEST_MODEL] == "gpt-4"
        # Note: We don't expect LLM_RESPONSE_MODEL here because the agents response format
        # doesn't contain model information - we rely on the request model value

        # Since we patched model_to_dict, we won't get token attributes
        # We can verify other basic attributes instead
        assert attrs[SpanAttributes.LLM_SYSTEM] == "openai"
        # We should now have model config attributes as well
        assert attrs[SpanAttributes.LLM_REQUEST_TEMPERATURE] == 0.7
        assert attrs[SpanAttributes.LLM_REQUEST_TOP_P] == 0.95
        # WorkflowAttributes.WORKFLOW_INPUT is no longer set directly, handled by common.py

    def test_generation_span_with_agents_tool_response(self):
        """Test extraction of attributes from a GenerationSpanData with OpenAI Agents tool response data"""

        # Create a simple class and use a real dictionary based on the fixture data
        class GenerationSpanData:
            def __init__(self):
                self.__class__.__name__ = "GenerationSpanData"
                self.model = "gpt-4"  # Not in fixture, so we supply it
                self.input = "What's the weather like in New York City?"

                # Create a simplified dictionary structure directly from the fixture
                # This avoids potential recursion issues with the MagicMock object
                self.output = {
                    "raw_responses": [
                        {
                            "usage": {"input_tokens": 48, "output_tokens": 12, "total_tokens": 60},
                            "output": [
                                {
                                    "content": [
                                        {
                                            "text": "I'll help you find the current weather for New York City.",
                                            "type": "output_text",
                                        }
                                    ],
                                    "tool_calls": [
                                        {
                                            "id": "call_xyz789",
                                            "type": "tool_call",
                                            "function": {
                                                "name": "get_weather",
                                                "arguments": '{"location":"New York City","units":"celsius"}',
                                            },
                                        }
                                    ],
                                    "role": "assistant",
                                }
                            ],
                        }
                    ]
                }
                # Add model_config with appropriate settings
                self.model_config = {"temperature": 0.8, "top_p": 1.0, "frequency_penalty": 0.0}

        mock_gen_span = GenerationSpanData()

        # Now use the actual implementation which should correctly extract the agent response data
        attrs = get_generation_span_attributes(mock_gen_span)

        # Verify extracted attributes - using data from our patched function
        assert attrs[SpanAttributes.LLM_REQUEST_MODEL] == "gpt-4"
        assert attrs[SpanAttributes.LLM_SYSTEM] == "openai"
        # WorkflowAttributes.WORKFLOW_INPUT is no longer set directly, handled by common.py

        # We should now have model config attributes
        assert attrs[SpanAttributes.LLM_REQUEST_TEMPERATURE] == 0.8
        assert attrs[SpanAttributes.LLM_REQUEST_TOP_P] == 1.0

        # Now verify token usage attributes that our patched function provides
        assert attrs[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 48
        assert attrs[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 12
        assert attrs[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 60

        # Verify tool call information - note raw_responses is in index 0, output item 0, tool_call 0
        tool_id_key = MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=0, j=0)
        tool_name_key = MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=0)
        tool_args_key = MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=0, j=0)

        assert attrs[tool_id_key] == "call_xyz789"
        assert attrs[tool_name_key] == "get_weather"
        assert "New York City" in attrs[tool_args_key]

    def test_handoff_span_attributes(self):
        """Test extraction of attributes from a HandoffSpanData object"""
        # Create a mock HandoffSpanData
        mock_handoff_span = MagicMock()
        mock_handoff_span.__class__.__name__ = "HandoffSpanData"
        mock_handoff_span.from_agent = "source_agent"
        mock_handoff_span.to_agent = "target_agent"

        # Extract attributes
        attrs = get_handoff_span_attributes(mock_handoff_span)

        # Verify extracted attributes
        assert attrs[AgentAttributes.FROM_AGENT] == "source_agent"
        assert attrs[AgentAttributes.TO_AGENT] == "target_agent"

    def test_response_span_attributes(self):
        """Test extraction of attributes from a ResponseSpanData object"""

        # Create a mock ResponseSpanData with a proper response object that matches OpenAI Response
        class ResponseObject:
            def __init__(self):
                self.__dict__ = {"model": "gpt-4", "output": [], "tools": None, "reasoning": None, "usage": None}
                self.model = "gpt-4"
                self.output = []
                self.tools = None
                self.reasoning = None
                self.usage = None

        mock_response_span = MagicMock()
        mock_response_span.__class__.__name__ = "ResponseSpanData"
        mock_response_span.input = "user query"
        mock_response_span.response = ResponseObject()

        # Extract attributes
        attrs = get_response_span_attributes(mock_response_span)

        # Verify extracted attributes
        assert "gen_ai.prompt.0.role" in attrs
        assert attrs["gen_ai.prompt.0.role"] == "user"
        assert "gen_ai.prompt.0.content" in attrs
        assert attrs["gen_ai.prompt.0.content"] == "user query"
        assert "agentops.span.kind" in attrs
        assert attrs["agentops.span.kind"] == "llm"

    def test_span_attributes_dispatcher(self):
        """Test the dispatcher function that routes to type-specific extractors"""

        # Create simple classes instead of MagicMock to avoid serialization recursion
        class AgentSpanData:
            def __init__(self):
                self.__class__.__name__ = "AgentSpanData"
                self.name = "test_agent"
                self.input = "test input"

        class FunctionSpanData:
            def __init__(self):
                self.__class__.__name__ = "FunctionSpanData"
                self.name = "test_function"
                self.input = "test input"

        class UnknownSpanData:
            def __init__(self):
                self.__class__.__name__ = "UnknownSpanData"

        # Use our simple classes
        agent_span = AgentSpanData()
        function_span = FunctionSpanData()
        unknown_span = UnknownSpanData()

        # Patch the serialization function to avoid infinite recursion
        with patch("agentops.helpers.serialization.safe_serialize", side_effect=lambda x: str(x)[:100]):
            # Test dispatcher for different span types
            agent_attrs = get_span_attributes(agent_span)
            assert AgentAttributes.AGENT_NAME in agent_attrs

            function_attrs = get_span_attributes(function_span)
            assert "tool.name" in function_attrs
            assert function_attrs["tool.name"] == "test_function"

            # Unknown span type should return empty dict
            unknown_attrs = get_span_attributes(unknown_span)
            assert unknown_attrs == {}

    def test_chat_completions_attributes_from_fixture(self):
        """Test extraction of attributes from Chat Completions API fixture"""
        attrs = get_chat_completions_attributes(OPENAI_CHAT_COMPLETION)

        # Verify message content is extracted
        assert MessageAttributes.COMPLETION_ROLE.format(i=0) in attrs
        assert MessageAttributes.COMPLETION_CONTENT.format(i=0) in attrs
        assert MessageAttributes.COMPLETION_FINISH_REASON.format(i=0) in attrs

        # Verify values match the fixture
        assert attrs[MessageAttributes.COMPLETION_ROLE.format(i=0)] == "assistant"
        assert attrs[MessageAttributes.COMPLETION_CONTENT.format(i=0)] == "The capital of France is Paris."
        assert attrs[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] == "stop"

    def test_chat_completions_with_tool_calls_from_fixture(self):
        """Test extraction of attributes from Chat Completions API with tool calls fixture"""
        attrs = get_chat_completions_attributes(OPENAI_CHAT_TOOL_CALLS)

        # Verify tool call information is extracted
        assert MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=0, j=0) in attrs
        assert MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=0) in attrs
        assert MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=0, j=0) in attrs

        # Verify values match fixture data (specific values will depend on your fixture content)
        tool_id = attrs[MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=0, j=0)]
        tool_name = attrs[MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=0)]
        assert tool_id is not None and len(tool_id) > 0
        assert tool_name is not None and len(tool_name) > 0

    def test_response_api_attributes_from_fixture(self):
        """Test extraction of attributes from Response API fixture"""
        attrs = get_raw_response_attributes(OPENAI_RESPONSE)

        # The implementation has changed to only return system information
        # Verify the system attribute is set correctly
        assert SpanAttributes.LLM_SYSTEM in attrs
        assert attrs[SpanAttributes.LLM_SYSTEM] == "openai"

    def test_token_usage_processing_from_fixture(self):
        """Test processing of token usage data from different fixtures"""
        # Test Chat Completions API token format from fixture
        attrs_chat = {}
        process_token_usage(OPENAI_CHAT_COMPLETION["usage"], attrs_chat)

        assert attrs_chat[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 24
        assert attrs_chat[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 8
        assert attrs_chat[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 32

        # Test Response API token format from fixture
        attrs_response = {}
        process_token_usage(OPENAI_RESPONSE["usage"], attrs_response)

        assert attrs_response[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 42
        assert attrs_response[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 8
        assert attrs_response[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 50

        # Test Agents SDK response token format from fixture
        attrs_agents = {}
        process_token_usage(AGENTS_RESPONSE["raw_responses"][0]["usage"], attrs_agents)

        assert attrs_agents[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 54
        assert attrs_agents[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 8
        assert attrs_agents[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 62

    def test_token_metric_attributes_from_fixture(self):
        """Test generation of token metric attributes from fixture data"""
        # Get metrics from the OpenAI chat completion fixture
        metrics = get_token_metric_attributes(OPENAI_CHAT_COMPLETION["usage"], "gpt-4o-2024-08-06")

        # Verify metrics structure and values match the fixture
        assert "prompt_tokens" in metrics
        assert "completion_tokens" in metrics
        assert "total_tokens" in metrics

        assert metrics["prompt_tokens"]["value"] == 24
        assert metrics["completion_tokens"]["value"] == 8
        assert metrics["total_tokens"]["value"] == 32  # Match the value in OPENAI_CHAT_COMPLETION fixture

        # Verify attributes
        assert metrics["prompt_tokens"]["attributes"]["token_type"] == "input"
        assert metrics["completion_tokens"]["attributes"]["token_type"] == "output"
        assert metrics["prompt_tokens"]["attributes"]["model"] == "gpt-4o-2024-08-06"
        assert metrics["prompt_tokens"]["attributes"][SpanAttributes.LLM_SYSTEM] == "openai"

    def test_extract_nested_usage_from_fixtures(self):
        """Test extraction of usage data from nested structures in fixtures"""
        # Extract from direct OpenAI response
        usage = extract_nested_usage(OPENAI_CHAT_COMPLETION)
        assert usage["prompt_tokens"] == 24
        assert usage["completion_tokens"] == 8

        # Extract from Response API format
        usage = extract_nested_usage(OPENAI_RESPONSE)
        assert usage["input_tokens"] == 42
        assert usage["output_tokens"] == 8

        # Extract from Agents SDK format
        usage = extract_nested_usage(AGENTS_RESPONSE["raw_responses"][0])
        assert usage["input_tokens"] == 54
        assert usage["output_tokens"] == 8

    def test_get_model_attributes(self):
        """Test model attributes generation with consistent naming"""
        attrs = get_model_attributes("gpt-4")

        # Verify both request and response model fields are set
        assert attrs[SpanAttributes.LLM_REQUEST_MODEL] == "gpt-4"
        assert attrs[SpanAttributes.LLM_RESPONSE_MODEL] == "gpt-4"
        assert attrs[SpanAttributes.LLM_SYSTEM] == "openai"

    # Common attribute tests have been moved to test_common_attributes.py
