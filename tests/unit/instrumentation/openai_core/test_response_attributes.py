"""
Tests for OpenAI Response API attribute extraction

This module contains tests for extracting attributes from the OpenAI Response API format.
It verifies that our instrumentation correctly extracts and transforms data from OpenAI API
responses into the appropriate OpenTelemetry span attributes.
"""

import json
import os
from unittest.mock import MagicMock, patch

from agentops.instrumentation.providers.openai.attributes.response import (
    get_response_kwarg_attributes,
    get_response_response_attributes,
    get_response_output_attributes,
    get_response_output_message_attributes,
    get_response_output_text_attributes,
    get_response_tools_attributes,
    get_response_usage_attributes,
    get_response_tool_web_search_attributes,
    get_response_tool_file_search_attributes,
    get_response_tool_computer_attributes,
)
from agentops.semconv import (
    SpanAttributes,
    MessageAttributes,
)


# Utility function to load fixtures
def load_fixture(fixture_name):
    """Load a test fixture from the fixtures directory"""
    fixture_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures", fixture_name)
    with open(fixture_path, "r") as f:
        return json.load(f)


# Load response test fixtures
OPENAI_RESPONSE = load_fixture("openai_response.json")  # Response API format with output array
OPENAI_RESPONSE_TOOL_CALLS = load_fixture("openai_response_tool_calls.json")  # Response API with tool calls


class MockResponse:
    """Mock Response object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)


class MockOutputMessage:
    """Mock ResponseOutputMessage object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)


class MockOutputText:
    """Mock ResponseOutputText object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)


class MockResponseUsage:
    """Mock ResponseUsage object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)


class MockOutputTokensDetails:
    """Mock OutputTokensDetails object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)


class MockReasoning:
    """Mock Reasoning object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)


class MockFunctionTool:
    """Mock FunctionTool object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        if not hasattr(self, "type"):
            self.type = "function"
        self.__dict__.update(data)


class MockWebSearchTool:
    """Mock WebSearchTool object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        if not hasattr(self, "type"):
            self.type = "web_search_preview"
        self.__dict__.update(data)


class MockFileSearchTool:
    """Mock FileSearchTool object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        if not hasattr(self, "type"):
            self.type = "file_search"
        self.__dict__.update(data)


class MockComputerTool:
    """Mock ComputerTool object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        if not hasattr(self, "type"):
            self.type = "computer_use_preview"
        self.__dict__.update(data)


class MockUserLocation:
    """Mock UserLocation object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        self.__dict__.update(data)


class MockFilters:
    """Mock Filters object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        self.__dict__.update(data)


class MockRankingOptions:
    """Mock RankingOptions object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        self.__dict__.update(data)


class MockFunctionWebSearch:
    """Mock ResponseFunctionWebSearch object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        if not hasattr(self, "type"):
            self.type = "web_search_call"
        self.__dict__.update(data)


class MockFileSearchToolCall:
    """Mock ResponseFileSearchToolCall object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        if not hasattr(self, "type"):
            self.type = "file_search_call"
        self.__dict__.update(data)


class MockComputerToolCall:
    """Mock ResponseComputerToolCall object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        if not hasattr(self, "type"):
            self.type = "computer_call"
        self.__dict__.update(data)


class MockReasoningItem:
    """Mock ResponseReasoningItem object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        if not hasattr(self, "type"):
            self.type = "reasoning"
        self.__dict__.update(data)


class MockFunctionToolCall:
    """Mock ResponseFunctionToolCall object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)


class MockResponseInputParam:
    """Mock ResponseInputParam object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)


class TestResponseAttributes:
    """Tests for OpenAI Response API attribute extraction"""

    def test_get_response_kwarg_attributes_with_string_input(self):
        """Test extraction of attributes from kwargs with string input"""
        kwargs = {
            "input": "What is the capital of France?",
            "model": "gpt-4o",
            "temperature": 0.7,
            "top_p": 1.0,
        }

        attributes = get_response_kwarg_attributes(kwargs)

        # Check that string input is correctly mapped to prompt attributes
        assert MessageAttributes.PROMPT_ROLE.format(i=0) in attributes
        assert attributes[MessageAttributes.PROMPT_ROLE.format(i=0)] == "user"
        assert MessageAttributes.PROMPT_CONTENT.format(i=0) in attributes
        assert attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] == "What is the capital of France?"

        # Check that model attribute is correctly mapped
        assert SpanAttributes.LLM_REQUEST_MODEL in attributes
        assert attributes[SpanAttributes.LLM_REQUEST_MODEL] == "gpt-4o"

    def test_get_response_kwarg_attributes_with_list_input(self):
        """Test extraction of attributes from kwargs with list input"""
        # Create a list of mock message objects
        messages = [
            MockResponseInputParam({"type": "text", "role": "system", "content": "You are a helpful assistant"}),
            MockResponseInputParam({"type": "text", "role": "user", "content": "What is the capital of France?"}),
        ]

        kwargs = {
            "input": messages,
            "model": "gpt-4o",
            "temperature": 0.7,
            "top_p": 1.0,
        }

        attributes = get_response_kwarg_attributes(kwargs)

        # Check that list input is correctly mapped to prompt attributes
        assert MessageAttributes.PROMPT_ROLE.format(i=0) in attributes
        assert attributes[MessageAttributes.PROMPT_ROLE.format(i=0)] == "system"
        assert MessageAttributes.PROMPT_CONTENT.format(i=0) in attributes
        assert attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] == "You are a helpful assistant"

        assert MessageAttributes.PROMPT_ROLE.format(i=1) in attributes
        assert attributes[MessageAttributes.PROMPT_ROLE.format(i=1)] == "user"
        assert MessageAttributes.PROMPT_CONTENT.format(i=1) in attributes
        assert attributes[MessageAttributes.PROMPT_CONTENT.format(i=1)] == "What is the capital of France?"

        # Check that model attribute is correctly mapped
        assert SpanAttributes.LLM_REQUEST_MODEL in attributes
        assert attributes[SpanAttributes.LLM_REQUEST_MODEL] == "gpt-4o"

    def test_get_response_kwarg_attributes_with_unsupported_input(self):
        """Test extraction of attributes from kwargs with unsupported input type"""
        kwargs = {
            "input": 123,  # Unsupported input type
            "model": "gpt-4o",
        }

        # Should not raise an exception but log a debug message
        with patch("agentops.instrumentation.providers.openai.attributes.response.logger.debug") as mock_logger:
            attributes = get_response_kwarg_attributes(kwargs)

            # Verify the debug message was logged
            mock_logger.assert_called_once()
            assert "'int'" in mock_logger.call_args[0][0]

            # Check that model attribute is still correctly mapped
            assert SpanAttributes.LLM_REQUEST_MODEL in attributes
            assert attributes[SpanAttributes.LLM_REQUEST_MODEL] == "gpt-4o"

    def test_get_response_response_attributes(self):
        """Test extraction of attributes from Response object"""
        # Create a mock Response object using the fixture data
        response_data = OPENAI_RESPONSE.copy()

        # We need to convert nested objects to appropriate classes for the code to handle them
        output = []
        for item in response_data["output"]:
            content = []
            for content_item in item["content"]:
                content.append(MockOutputText(content_item))
            output.append(MockOutputMessage({**item, "content": content}))

        usage = MockResponseUsage(
            {
                **response_data["usage"],
                "output_tokens_details": MockOutputTokensDetails(response_data["usage"]["output_tokens_details"]),
            }
        )

        reasoning = MockReasoning(response_data["reasoning"])

        # Set __dict__ to ensure attribute extraction works properly
        mock_response = MockResponse(
            {
                **response_data,
                "output": output,
                "usage": usage,
                "reasoning": reasoning,
                "tools": [],
                "__dict__": {**response_data, "output": output, "usage": usage, "reasoning": reasoning, "tools": []},
            }
        )

        # Patch the Response and other type checks for simpler testing
        with patch(
            "agentops.instrumentation.providers.openai.attributes.response.ResponseOutputMessage", MockOutputMessage
        ):
            with patch(
                "agentops.instrumentation.providers.openai.attributes.response.ResponseOutputText", MockOutputText
            ):
                # Extract attributes
                attributes = get_response_response_attributes(mock_response)

                # Check that basic attributes are extracted
                assert SpanAttributes.LLM_RESPONSE_ID in attributes
                assert attributes[SpanAttributes.LLM_RESPONSE_ID] == response_data["id"]
                assert SpanAttributes.LLM_RESPONSE_MODEL in attributes
                assert attributes[SpanAttributes.LLM_RESPONSE_MODEL] == response_data["model"]
                assert SpanAttributes.LLM_OPENAI_RESPONSE_INSTRUCTIONS in attributes
                assert attributes[SpanAttributes.LLM_OPENAI_RESPONSE_INSTRUCTIONS] == response_data["instructions"]

        # Check usage attributes
        assert SpanAttributes.LLM_USAGE_PROMPT_TOKENS in attributes
        assert attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == response_data["usage"]["input_tokens"]
        assert SpanAttributes.LLM_USAGE_COMPLETION_TOKENS in attributes
        assert attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == response_data["usage"]["output_tokens"]
        assert SpanAttributes.LLM_USAGE_TOTAL_TOKENS in attributes
        assert attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == response_data["usage"]["total_tokens"]

    def test_get_response_output_attributes_simple(self):
        """Test extraction of attributes from output list - simple case"""
        # Now just verify the function exists and doesn't throw an exception
        output = []  # Empty list is fine for this test

        # Patch all the type checks to make testing simpler
        with patch(
            "agentops.instrumentation.providers.openai.attributes.response.ResponseOutputMessage", MockOutputMessage
        ):
            with patch(
                "agentops.instrumentation.providers.openai.attributes.response.ResponseOutputText", MockOutputText
            ):
                with patch(
                    "agentops.instrumentation.providers.openai.attributes.response.ResponseFunctionToolCall",
                    MockFunctionToolCall,
                ):
                    result = get_response_output_attributes(output)

                    # Simply verify it returns a dictionary
                    assert isinstance(result, dict)

    def test_get_response_output_message_attributes(self):
        """Test extraction of attributes from output message"""
        # Create a simplest test we can - just verify the function exists
        # and can be called without exception

        # Patch the ResponseOutputText class to make testing simpler
        with patch("agentops.instrumentation.providers.openai.attributes.response.ResponseOutputText", MockOutputText):
            # Create a minimal mock with required attributes
            message = MockOutputMessage(
                {
                    "id": "msg_12345",
                    "content": [],  # Empty content for simplicity
                    "role": "assistant",
                    "status": "completed",
                    "type": "message",
                }
            )

            # Call the function
            result = get_response_output_message_attributes(0, message)

            # Verify basic expected attributes
            assert isinstance(result, dict)

    def test_get_response_output_text_attributes(self):
        """Test extraction of attributes from output text"""
        # Create a mock text content
        text = MockOutputText(
            {
                "annotations": [
                    {
                        "end_index": 636,
                        "start_index": 538,
                        "title": "5 AI Agent Frameworks Compared",
                        "type": "url_citation",
                        "url": "https://www.kdnuggets.com/5-ai-agent-frameworks-compared",
                    }
                ],
                "text": "CrewAI is the top AI agent library.",
                "type": "output_text",
            }
        )

        # The function doesn't use the mock directly but extracts attributes from it
        # Using _extract_attributes_from_mapping_with_index internally
        # We'll test by using patch to simulate the extraction

        with patch(
            "agentops.instrumentation.providers.openai.attributes.response._extract_attributes_from_mapping_with_index"
        ) as mock_extract:
            # Set up the mock to return expected attributes
            expected_attributes = {
                MessageAttributes.COMPLETION_ANNOTATION_END_INDEX.format(i=0, j=0): 636,
                MessageAttributes.COMPLETION_ANNOTATION_START_INDEX.format(i=0, j=1): 538,
                MessageAttributes.COMPLETION_ANNOTATION_TITLE.format(i=0, j=2): "5 AI Agent Frameworks Compared",
                MessageAttributes.COMPLETION_ANNOTATION_TYPE.format(i=0, j=3): "url_citation",
                MessageAttributes.COMPLETION_ANNOTATION_URL.format(
                    i=0, j=5
                ): "https://www.kdnuggets.com/5-ai-agent-frameworks-compared",
                MessageAttributes.COMPLETION_CONTENT.format(i=0): "CrewAI is the top AI agent library.",
                MessageAttributes.COMPLETION_TYPE.format(i=0): "output_text",
            }
            mock_extract.return_value = expected_attributes

            # Call the function
            attributes = get_response_output_text_attributes(0, text)

            # Verify mock was called with correct arguments
            mock_extract.assert_called_once()

            # Check that the return value matches our expected attributes
            assert attributes == expected_attributes

    def test_get_response_output_attributes_comprehensive(self):
        """Test extraction of attributes from output items with all output types"""
        # Create a mock response output list with all different output types
        message = MockOutputMessage(
            {
                "id": "msg_12345",
                "content": [
                    MockOutputText(
                        {
                            "text": "This is a test message",
                            "type": "output_text",
                            "annotations": [
                                {
                                    "end_index": 636,
                                    "start_index": 538,
                                    "title": "Test title",
                                    "type": "url_citation",
                                    "url": "www.test.com",
                                }
                            ],
                        }
                    )
                ],
                "role": "assistant",
                "status": "completed",
                "type": "message",
            }
        )

        tool_call = MockFunctionToolCall(
            {"id": "call_67890", "name": "get_weather", "arguments": '{"location":"Paris"}', "type": "function"}
        )

        web_search = MockFunctionWebSearch({"id": "ws_12345", "status": "completed", "type": "web_search_call"})

        file_search = MockFileSearchToolCall(
            {"id": "fsc_12345", "queries": ["search term"], "status": "completed", "type": "file_search_call"}
        )

        computer_call = MockComputerToolCall({"id": "comp_12345", "status": "completed", "type": "computer_call"})

        reasoning_item = MockReasoningItem({"id": "reason_12345", "status": "completed", "type": "reasoning"})

        # Create an unrecognized output item to test error handling
        unrecognized_item = MagicMock()
        unrecognized_item.type = "unknown_type"

        # Patch all the necessary type checks and logger
        with (
            patch(
                "agentops.instrumentation.providers.openai.attributes.response.ResponseOutputMessage", MockOutputMessage
            ),
            patch("agentops.instrumentation.providers.openai.attributes.response.ResponseOutputText", MockOutputText),
            patch(
                "agentops.instrumentation.providers.openai.attributes.response.ResponseFunctionToolCall",
                MockFunctionToolCall,
            ),
            patch(
                "agentops.instrumentation.providers.openai.attributes.response.ResponseFunctionWebSearch",
                MockFunctionWebSearch,
            ),
            patch(
                "agentops.instrumentation.providers.openai.attributes.response.ResponseFileSearchToolCall",
                MockFileSearchToolCall,
            ),
            patch(
                "agentops.instrumentation.providers.openai.attributes.response.ResponseComputerToolCall",
                MockComputerToolCall,
            ),
            patch(
                "agentops.instrumentation.providers.openai.attributes.response.ResponseReasoningItem", MockReasoningItem
            ),
            patch("agentops.instrumentation.providers.openai.attributes.response.logger.debug") as mock_logger,
        ):
            # Test with an output list containing all different types of output items
            output = [message, tool_call, web_search, file_search, computer_call, reasoning_item, unrecognized_item]

            # Call the function
            attributes = get_response_output_attributes(output)

            # Check that it extracted attributes from all items
            assert isinstance(attributes, dict)

            # Check message attributes were extracted (index 0)
            assert MessageAttributes.COMPLETION_ROLE.format(i=0) in attributes
            assert attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] == "assistant"
            assert MessageAttributes.COMPLETION_CONTENT.format(i=0) in attributes
            assert attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] == "This is a test message"

            # Check function tool call attributes were extracted (index 1)
            tool_attr_key = MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=1, j=0)
            assert tool_attr_key in attributes
            assert attributes[tool_attr_key] == "call_67890"

            # Check web search attributes were extracted (index 2)
            web_attr_key = MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=2, j=0)
            assert web_attr_key in attributes
            assert attributes[web_attr_key] == "ws_12345"

            # Verify that logger was called for unrecognized item
            assert any(
                call.args[0].startswith("[agentops.instrumentation.openai.response]")
                for call in mock_logger.call_args_list
            )

    def test_get_response_tools_attributes(self):
        """Test extraction of attributes from tools list"""
        # Create a mock function tool
        function_tool = MockFunctionTool(
            {
                "name": "get_weather",
                "parameters": {"properties": {"location": {"type": "string"}}, "required": ["location"]},
                "description": "Get weather information for a location",
                "type": "function",
                "strict": True,
            }
        )

        # Patch all tool types to make testing simpler
        with patch("agentops.instrumentation.providers.openai.attributes.response.FunctionTool", MockFunctionTool):
            with patch("agentops.instrumentation.providers.openai.attributes.response.WebSearchTool", MagicMock):
                with patch("agentops.instrumentation.providers.openai.attributes.response.FileSearchTool", MagicMock):
                    with patch("agentops.instrumentation.providers.openai.attributes.response.ComputerTool", MagicMock):
                        # Test with a function tool
                        tools = [function_tool]

                        # Call the function
                        result = get_response_tools_attributes(tools)

                        # Verify extracted attributes
                        assert isinstance(result, dict)
                        assert MessageAttributes.TOOL_CALL_TYPE.format(i=0) in result
                        assert result[MessageAttributes.TOOL_CALL_TYPE.format(i=0)] == "function"
                        assert MessageAttributes.TOOL_CALL_NAME.format(i=0) in result
                        assert result[MessageAttributes.TOOL_CALL_NAME.format(i=0)] == "get_weather"
                        assert MessageAttributes.TOOL_CALL_DESCRIPTION.format(i=0) in result
                        assert (
                            result[MessageAttributes.TOOL_CALL_DESCRIPTION.format(i=0)]
                            == "Get weather information for a location"
                        )

    def test_get_response_tool_web_search_attributes(self):
        """Test extraction of attributes from web search tool"""
        # Create a mock web search tool
        user_location = MockUserLocation({"type": "approximate", "country": "US"})

        web_search_tool = MockWebSearchTool(
            {"type": "web_search_preview", "search_context_size": "medium", "user_location": user_location}
        )

        # Call the function directly
        with patch("agentops.instrumentation.providers.openai.attributes.response.WebSearchTool", MockWebSearchTool):
            result = get_response_tool_web_search_attributes(web_search_tool, 0)

            # Verify attributes
            assert isinstance(result, dict)
            assert MessageAttributes.TOOL_CALL_NAME.format(i=0) in result
            assert result[MessageAttributes.TOOL_CALL_NAME.format(i=0)] == "web_search_preview"
            assert MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0) in result
            # Parameters should be serialized
            assert "search_context_size" in result[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0)]
            assert "user_location" in result[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0)]

    def test_get_response_tool_file_search_attributes(self):
        """Test extraction of attributes from file search tool"""
        # Create a mock file search tool
        filters = MockFilters({"key": "value"})

        ranking_options = MockRankingOptions({"ranker": "default-2024-11-15", "score_threshold": 0.8})

        file_search_tool = MockFileSearchTool(
            {
                "type": "file_search",
                "vector_store_ids": ["store_123", "store_456"],
                "filters": filters,
                "max_num_results": 10,
                "ranking_options": ranking_options,
            }
        )

        # Call the function directly
        with patch("agentops.instrumentation.providers.openai.attributes.response.FileSearchTool", MockFileSearchTool):
            result = get_response_tool_file_search_attributes(file_search_tool, 0)

            # Verify attributes
            assert isinstance(result, dict)
            assert MessageAttributes.TOOL_CALL_TYPE.format(i=0) in result
            assert result[MessageAttributes.TOOL_CALL_TYPE.format(i=0)] == "file_search"
            assert MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0) in result
            # Parameters should be serialized
            assert "vector_store_ids" in result[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0)]
            assert "filters" in result[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0)]
            assert "max_num_results" in result[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0)]
            assert "ranking_options" in result[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0)]

    def test_get_response_tool_computer_attributes(self):
        """Test extraction of attributes from computer tool"""
        # Create a mock computer tool
        computer_tool = MockComputerTool(
            {"type": "computer_use_preview", "display_height": 1080.0, "display_width": 1920.0, "environment": "mac"}
        )

        # Call the function directly
        with patch("agentops.instrumentation.providers.openai.attributes.response.ComputerTool", MockComputerTool):
            result = get_response_tool_computer_attributes(computer_tool, 0)

            # Verify attributes
            assert isinstance(result, dict)
            assert MessageAttributes.TOOL_CALL_TYPE.format(i=0) in result
            assert result[MessageAttributes.TOOL_CALL_TYPE.format(i=0)] == "computer_use_preview"
            assert MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0) in result
            # Parameters should be serialized
            assert "display_height" in result[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0)]
            assert "display_width" in result[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0)]
            assert "environment" in result[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0)]

    def test_get_response_usage_attributes(self):
        """Test extraction of attributes from usage data"""
        # Create a more comprehensive test for usage attributes

        # Patch the OutputTokensDetails class to make testing simpler
        with patch(
            "agentops.instrumentation.providers.openai.attributes.response.OutputTokensDetails", MockOutputTokensDetails
        ):
            with patch("agentops.instrumentation.providers.openai.attributes.response.InputTokensDetails", MagicMock):
                # Test with all fields
                usage = MockResponseUsage(
                    {
                        "input_tokens": 50,
                        "output_tokens": 20,
                        "total_tokens": 70,
                        "output_tokens_details": MockOutputTokensDetails({"reasoning_tokens": 5}),
                        "input_tokens_details": {"cached_tokens": 10},
                        "__dict__": {
                            "input_tokens": 50,
                            "output_tokens": 20,
                            "total_tokens": 70,
                            "output_tokens_details": MockOutputTokensDetails({"reasoning_tokens": 5}),
                            "input_tokens_details": {"cached_tokens": 10},
                        },
                    }
                )

                # Test without token details (edge cases)
                usage_without_details = MockResponseUsage(
                    {
                        "input_tokens": 30,
                        "output_tokens": 15,
                        "total_tokens": 45,
                        "output_tokens_details": None,
                        "input_tokens_details": None,
                        "__dict__": {
                            "input_tokens": 30,
                            "output_tokens": 15,
                            "total_tokens": 45,
                            "output_tokens_details": None,
                            "input_tokens_details": None,
                        },
                    }
                )

                # Call the function for complete usage
                result = get_response_usage_attributes(usage)

                # Verify it returns a dictionary with all attributes
                assert isinstance(result, dict)
                assert SpanAttributes.LLM_USAGE_PROMPT_TOKENS in result
                assert result[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 50
                assert SpanAttributes.LLM_USAGE_COMPLETION_TOKENS in result
                assert result[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 20
                assert SpanAttributes.LLM_USAGE_TOTAL_TOKENS in result
                assert result[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 70
                assert SpanAttributes.LLM_USAGE_REASONING_TOKENS in result
                assert result[SpanAttributes.LLM_USAGE_REASONING_TOKENS] == 5
                assert SpanAttributes.LLM_USAGE_CACHE_READ_INPUT_TOKENS in result
                assert result[SpanAttributes.LLM_USAGE_CACHE_READ_INPUT_TOKENS] == 10

                # Call the function for usage without details
                result_without_details = get_response_usage_attributes(usage_without_details)

                # Verify basic attributes are still present
                assert isinstance(result_without_details, dict)
                assert SpanAttributes.LLM_USAGE_PROMPT_TOKENS in result_without_details
                assert result_without_details[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 30
                assert SpanAttributes.LLM_USAGE_COMPLETION_TOKENS in result_without_details
                assert result_without_details[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 15
                assert SpanAttributes.LLM_USAGE_TOTAL_TOKENS in result_without_details
                assert result_without_details[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 45
                # Detailed attributes shouldn't be present
                assert SpanAttributes.LLM_USAGE_REASONING_TOKENS not in result_without_details
                assert SpanAttributes.LLM_USAGE_CACHE_READ_INPUT_TOKENS not in result_without_details
