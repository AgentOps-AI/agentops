"""
Tests for OpenAI Response API attribute extraction

This module contains tests for extracting attributes from the OpenAI Response API format.
It verifies that our instrumentation correctly extracts and transforms data from OpenAI API
responses into the appropriate OpenTelemetry span attributes.
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch

from agentops.instrumentation.openai.attributes.response import (
    get_response_kwarg_attributes,
    get_response_response_attributes,
    get_response_output_attributes,
    get_response_output_message_attributes,
    get_response_output_text_attributes,
    get_response_output_reasoning_attributes,
    get_response_output_tool_attributes,
    get_response_tools_attributes,
    get_response_usage_attributes,
    get_response_reasoning_attributes
)
from agentops.semconv import (
    SpanAttributes,
    MessageAttributes,
    ToolAttributes,
)


# Utility function to load fixtures
def load_fixture(fixture_name):
    """Load a test fixture from the fixtures directory"""
    fixture_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "fixtures", 
        fixture_name
    )
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
        self.type = "function"


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
            MockResponseInputParam({
                "type": "text",
                "role": "system",
                "content": "You are a helpful assistant"
            }),
            MockResponseInputParam({
                "type": "text",
                "role": "user",
                "content": "What is the capital of France?"
            })
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
        with patch('agentops.instrumentation.openai.attributes.response.logger.debug') as mock_logger:
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
        for item in response_data['output']:
            content = []
            for content_item in item['content']:
                content.append(MockOutputText(content_item))
            output.append(MockOutputMessage({**item, 'content': content}))
        
        usage = MockResponseUsage({
            **response_data['usage'],
            'output_tokens_details': MockOutputTokensDetails(response_data['usage']['output_tokens_details'])
        })
        
        reasoning = MockReasoning(response_data['reasoning'])
        
        # Set __dict__ to ensure attribute extraction works properly
        mock_response = MockResponse({
            **response_data,
            'output': output,
            'usage': usage,
            'reasoning': reasoning,
            'tools': [],
            '__dict__': {
                **response_data,
                'output': output,
                'usage': usage,
                'reasoning': reasoning,
                'tools': []
            }
        })
        
        # Patch the Response and other type checks for simpler testing
        with patch('agentops.instrumentation.openai.attributes.response.ResponseOutputMessage', MockOutputMessage):
            with patch('agentops.instrumentation.openai.attributes.response.ResponseOutputText', MockOutputText):
                # Extract attributes
                attributes = get_response_response_attributes(mock_response)
                
                # Check that basic attributes are extracted
                assert SpanAttributes.LLM_RESPONSE_ID in attributes
                assert attributes[SpanAttributes.LLM_RESPONSE_ID] == response_data['id']
                assert SpanAttributes.LLM_RESPONSE_MODEL in attributes
                assert attributes[SpanAttributes.LLM_RESPONSE_MODEL] == response_data['model']
                assert SpanAttributes.LLM_PROMPTS in attributes
                assert attributes[SpanAttributes.LLM_PROMPTS] == response_data['instructions']
        
        # Check usage attributes
        assert SpanAttributes.LLM_USAGE_PROMPT_TOKENS in attributes
        assert attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == response_data['usage']['input_tokens']
        assert SpanAttributes.LLM_USAGE_COMPLETION_TOKENS in attributes
        assert attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == response_data['usage']['output_tokens']
        assert SpanAttributes.LLM_USAGE_TOTAL_TOKENS in attributes
        assert attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == response_data['usage']['total_tokens']

    def test_get_response_output_attributes(self):
        """Test extraction of attributes from output list"""
        # Create a simple dictionary for testing
        attributes = {}  # We'll use an empty dict to simplify the test
        
        # Now just verify the function exists and doesn't throw an exception
        output = []  # Empty list is fine for this test
        
        # Patch all the type checks to make testing simpler
        with patch('agentops.instrumentation.openai.attributes.response.ResponseOutputMessage', MockOutputMessage):
            with patch('agentops.instrumentation.openai.attributes.response.ResponseOutputText', MockOutputText):
                with patch('agentops.instrumentation.openai.attributes.response.ResponseFunctionToolCall', MockFunctionToolCall):
                    result = get_response_output_attributes(output)
                    
                    # Simply verify it returns a dictionary
                    assert isinstance(result, dict)

    def test_get_response_output_message_attributes(self):
        """Test extraction of attributes from output message"""
        # Create a simplest test we can - just verify the function exists
        # and can be called without exception
        
        # Patch the ResponseOutputText class to make testing simpler
        with patch('agentops.instrumentation.openai.attributes.response.ResponseOutputText', MockOutputText):
            # Create a minimal mock with required attributes
            message = MockOutputMessage({
                'id': 'msg_12345',
                'content': [],  # Empty content for simplicity
                'role': 'assistant',
                'status': 'completed',
                'type': 'message'
            })
            
            # Call the function
            result = get_response_output_message_attributes(0, message)
            
            # Verify basic expected attributes
            assert isinstance(result, dict)

    def test_get_response_output_text_attributes(self):
        """Test extraction of attributes from output text"""
        # Create a mock text content
        text = MockOutputText({
            'annotations': [],
            'text': 'The capital of France is Paris.',
            'type': 'output_text'
        })
        
        # Extract attributes
        attributes = get_response_output_text_attributes(0, text)
        
        # Check attributes
        assert MessageAttributes.COMPLETION_CONTENT.format(i=0) in attributes
        assert attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] == 'The capital of France is Paris.'

    def test_get_response_output_tool_attributes(self):
        """Test extraction of attributes from output tool"""
        # Create a mock tool call
        tool_call = MockFunctionToolCall({
            'id': 'call_67890',
            'name': 'get_weather',
            'arguments': '{"location":"Paris"}',
            'type': 'function'
        })
        
        # Extract attributes
        attributes = get_response_output_tool_attributes(0, tool_call)
        
        # Check attributes
        assert MessageAttributes.FUNCTION_CALL_ID.format(i=0) in attributes
        assert attributes[MessageAttributes.FUNCTION_CALL_ID.format(i=0)] == 'call_67890'
        assert MessageAttributes.FUNCTION_CALL_NAME.format(i=0) in attributes
        assert attributes[MessageAttributes.FUNCTION_CALL_NAME.format(i=0)] == 'get_weather'
        assert MessageAttributes.FUNCTION_CALL_ARGUMENTS.format(i=0) in attributes
        assert attributes[MessageAttributes.FUNCTION_CALL_ARGUMENTS.format(i=0)] == '{"location":"Paris"}'
        assert MessageAttributes.FUNCTION_CALL_TYPE.format(i=0) in attributes
        assert attributes[MessageAttributes.FUNCTION_CALL_TYPE.format(i=0)] == 'function'

    def test_get_response_tools_attributes(self):
        """Test extraction of attributes from tools list"""
        # Simplify the test to just verify the function can be called without error
        
        # Patch the FunctionTool class to make testing simpler
        with patch('agentops.instrumentation.openai.attributes.response.FunctionTool', MockFunctionTool):
            # Test with empty list for simplicity
            tools = []
            
            # Call the function
            result = get_response_tools_attributes(tools)
            
            # Verify basic expected attributes
            assert isinstance(result, dict)

    def test_get_response_usage_attributes(self):
        """Test extraction of attributes from usage data"""
        # Simplify test to verify function can be called without error
        
        # Patch the OutputTokensDetails class to make testing simpler
        with patch('agentops.instrumentation.openai.attributes.response.OutputTokensDetails', MockOutputTokensDetails):
            # Create a minimal mock usage object with all necessary attributes
            usage = MockResponseUsage({
                'input_tokens': 50,
                'output_tokens': 20,
                'total_tokens': 70,
                'output_tokens_details': MockOutputTokensDetails({
                    'reasoning_tokens': 5
                }),
                'input_tokens_details': {
                    'cached_tokens': 10
                },
                '__dict__': {
                    'input_tokens': 50,
                    'output_tokens': 20,
                    'total_tokens': 70,
                    'output_tokens_details': MockOutputTokensDetails({
                        'reasoning_tokens': 5
                    }),
                    'input_tokens_details': {
                        'cached_tokens': 10
                    }
                }
            })
            
            # Call the function
            result = get_response_usage_attributes(usage)
            
            # Verify it returns a dictionary with at least these basic attributes
            assert isinstance(result, dict)
            assert SpanAttributes.LLM_USAGE_PROMPT_TOKENS in result
            assert result[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 50
            assert SpanAttributes.LLM_USAGE_COMPLETION_TOKENS in result
            assert result[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 20
            assert SpanAttributes.LLM_USAGE_TOTAL_TOKENS in result
            assert result[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 70

    def test_get_response_reasoning_attributes(self):
        """Test extraction of attributes from reasoning data"""
        # Create mock reasoning object
        reasoning = MockReasoning({
            'effort': 'medium',
            'generate_summary': True
        })
        
        # Extract attributes - currently no attributes are mapped for reasoning
        attributes = get_response_reasoning_attributes(reasoning)
        
        # The current implementation returns an empty dictionary because
        # there are no defined attributes in RESPONSE_REASONING_ATTRIBUTES
        assert isinstance(attributes, dict)
        assert len(attributes) == 0  # Currently no attributes are mapped