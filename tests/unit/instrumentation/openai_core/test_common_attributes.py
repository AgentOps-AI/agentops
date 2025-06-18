"""
Tests for OpenAI common attribute handling

This module contains tests for common attribute handling functions in the OpenAI instrumentation,
specifically focusing on the get_response_attributes function which combines various attribute
extraction functions.
"""

from unittest.mock import patch

from agentops.instrumentation.providers.openai.attributes.common import (
    get_common_instrumentation_attributes,
    get_response_attributes,
)
from agentops.instrumentation.providers.openai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.semconv import SpanAttributes, MessageAttributes, InstrumentationAttributes


class MockResponse:
    """Mock Response object for testing"""

    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)


class TestCommonAttributes:
    """Tests for OpenAI common attribute handling functions"""

    def test_get_common_instrumentation_attributes(self):
        """Test that common instrumentation attributes are correctly generated"""
        # Call the function
        attributes = get_common_instrumentation_attributes()

        # Verify library attributes are set
        assert InstrumentationAttributes.LIBRARY_NAME in attributes
        assert attributes[InstrumentationAttributes.LIBRARY_NAME] == LIBRARY_NAME
        assert InstrumentationAttributes.LIBRARY_VERSION in attributes
        assert attributes[InstrumentationAttributes.LIBRARY_VERSION] == LIBRARY_VERSION

        # Verify common attributes from parent function are included
        # (these would be added by get_common_attributes)
        assert InstrumentationAttributes.NAME in attributes

    def test_get_response_attributes_with_kwargs(self):
        """Test that response attributes are correctly extracted from kwargs"""
        # Create kwargs
        kwargs = {
            "input": "What is the capital of France?",
            "model": "gpt-4o",
            "temperature": 0.7,
            "top_p": 1.0,
        }

        # Mock the kwarg extraction function
        with patch(
            "agentops.instrumentation.providers.openai.attributes.common.get_response_kwarg_attributes"
        ) as mock_kwarg_attributes:
            mock_kwarg_attributes.return_value = {
                MessageAttributes.PROMPT_ROLE.format(i=0): "user",
                MessageAttributes.PROMPT_CONTENT.format(i=0): "What is the capital of France?",
                SpanAttributes.LLM_REQUEST_MODEL: "gpt-4o",
            }

            # Call the function
            attributes = get_response_attributes(kwargs=kwargs)

            # Verify kwarg extraction was called
            mock_kwarg_attributes.assert_called_once_with(kwargs)

            # Verify attributes from kwarg extraction are included
            assert MessageAttributes.PROMPT_ROLE.format(i=0) in attributes
            assert attributes[MessageAttributes.PROMPT_ROLE.format(i=0)] == "user"
            assert MessageAttributes.PROMPT_CONTENT.format(i=0) in attributes
            assert attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] == "What is the capital of France?"
            assert SpanAttributes.LLM_REQUEST_MODEL in attributes
            assert attributes[SpanAttributes.LLM_REQUEST_MODEL] == "gpt-4o"

    def test_get_response_attributes_with_return_value(self):
        """Test that response attributes are correctly extracted from return value"""
        # Create a mock Response object with all required attributes
        response = MockResponse(
            {
                "id": "resp_12345",
                "model": "gpt-4o",
                "instructions": "You are a helpful assistant.",
                "output": [],
                "tools": [],
                "reasoning": None,
                "usage": None,
                "__dict__": {
                    "id": "resp_12345",
                    "model": "gpt-4o",
                    "instructions": "You are a helpful assistant.",
                    "output": [],
                    "tools": [],
                    "reasoning": None,
                    "usage": None,
                },
            }
        )

        # Use direct patching of Response class check instead
        with patch("agentops.instrumentation.providers.openai.attributes.common.Response", MockResponse):
            # Call the function
            attributes = get_response_attributes(return_value=response)

            # Verify attributes are included without mocking the specific function
            # Just verify some basic attributes are set
            assert InstrumentationAttributes.LIBRARY_NAME in attributes
            assert attributes[InstrumentationAttributes.LIBRARY_NAME] == LIBRARY_NAME
            assert InstrumentationAttributes.LIBRARY_VERSION in attributes
            assert attributes[InstrumentationAttributes.LIBRARY_VERSION] == LIBRARY_VERSION

    def test_get_response_attributes_with_both(self):
        """Test that response attributes are correctly extracted from both kwargs and return value"""
        # Create kwargs
        kwargs = {
            "input": "What is the capital of France?",
            "model": "gpt-4o",
            "temperature": 0.7,
            "top_p": 1.0,
        }

        # Create a mock Response object with all required attributes
        response = MockResponse(
            {
                "id": "resp_12345",
                "model": "gpt-4o",
                "instructions": "You are a helpful assistant.",
                "output": [],
                "tools": [],
                "reasoning": None,
                "usage": None,
                "__dict__": {
                    "id": "resp_12345",
                    "model": "gpt-4o",
                    "instructions": "You are a helpful assistant.",
                    "output": [],
                    "tools": [],
                    "reasoning": None,
                    "usage": None,
                },
            }
        )

        # Instead of mocking the internal functions, test the integration directly
        with patch("agentops.instrumentation.providers.openai.attributes.common.Response", MockResponse):
            # Call the function
            attributes = get_response_attributes(kwargs=kwargs, return_value=response)

            # Verify the key response attributes are in the final attributes dict
            assert InstrumentationAttributes.LIBRARY_NAME in attributes
            assert attributes[InstrumentationAttributes.LIBRARY_NAME] == LIBRARY_NAME

    def test_get_response_attributes_with_unexpected_return_type(self):
        """Test handling of unexpected return value type"""
        # Create an object that's not a Response
        not_a_response = "not a response"

        # Should log a debug message but not raise an exception
        with patch("agentops.instrumentation.providers.openai.attributes.common.logger.debug") as mock_logger:
            # Call the function
            attributes = get_response_attributes(return_value=not_a_response)

            # Verify debug message was logged
            mock_logger.assert_called_once()
            assert "unexpected return type" in mock_logger.call_args[0][0]

            # Verify common attributes are still present
            assert InstrumentationAttributes.NAME in attributes
            assert InstrumentationAttributes.LIBRARY_NAME in attributes
