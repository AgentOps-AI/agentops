"""
Tests for OpenAI Stream Wrapper Attribute Delegation

This module contains tests for the OpenAI stream wrapper classes to ensure
proper attribute delegation to the underlying stream objects.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from agentops.instrumentation.providers.openai.stream_wrapper import OpenAIAsyncStreamWrapper, OpenaiStreamWrapper


class TestOpenaiStreamWrapper:
    """Tests for sync OpenAI stream wrapper attribute delegation"""

    def test_getattr_delegates_to_stream(self):
        """Test that __getattr__ properly delegates to underlying stream"""
        mock_stream = Mock()
        mock_stream.choices = [{"delta": {"content": "test content"}}]
        mock_stream.model = "gpt-4"
        mock_stream.id = "test-stream-id"
        mock_stream.usage = {"prompt_tokens": 10, "completion_tokens": 5}

        mock_span = Mock()

        wrapper = OpenaiStreamWrapper(mock_stream, mock_span, {})

        assert wrapper.choices == mock_stream.choices
        assert wrapper.model == mock_stream.model
        assert wrapper.id == mock_stream.id
        assert wrapper.usage == mock_stream.usage

    def test_getattr_raises_attributeerror_for_missing_attributes(self):
        """Test that __getattr__ raises AttributeError for missing attributes"""
        mock_stream = Mock()
        del mock_stream.nonexistent_attribute  # Ensure it doesn't exist

        mock_span = Mock()

        wrapper = OpenaiStreamWrapper(mock_stream, mock_span, {})

        with pytest.raises(AttributeError):
            _ = wrapper.nonexistent_attribute


class TestOpenAIAsyncStreamWrapper:
    """Tests for async OpenAI stream wrapper attribute delegation"""

    def test_getattr_delegates_to_stream(self):
        """Test that __getattr__ properly delegates to underlying stream"""
        mock_stream = AsyncMock()
        mock_stream.choices = [{"delta": {"content": "test content"}}]
        mock_stream.model = "gpt-4"
        mock_stream.id = "test-async-stream-id"
        mock_stream.usage = {"prompt_tokens": 15, "completion_tokens": 8}

        mock_span = Mock()

        wrapper = OpenAIAsyncStreamWrapper(mock_stream, mock_span, {})

        assert wrapper.choices == mock_stream.choices
        assert wrapper.model == mock_stream.model
        assert wrapper.id == mock_stream.id
        assert wrapper.usage == mock_stream.usage

    def test_getattr_raises_attributeerror_for_missing_attributes(self):
        """Test that __getattr__ raises AttributeError for missing attributes"""
        mock_stream = AsyncMock()
        del mock_stream.nonexistent_attribute  # Ensure it doesn't exist

        mock_span = Mock()

        wrapper = OpenAIAsyncStreamWrapper(mock_stream, mock_span, {})

        with pytest.raises(AttributeError):
            _ = wrapper.nonexistent_attribute

    def test_choices_attribute_specifically(self):
        """Test the specific 'choices' attribute that was causing the original error"""
        mock_stream = AsyncMock()
        mock_stream.choices = [Mock(delta=Mock(content="Hello")), Mock(delta=Mock(content=" world"))]

        mock_span = Mock()

        wrapper = OpenAIAsyncStreamWrapper(mock_stream, mock_span, {})

        choices = wrapper.choices
        assert len(choices) == 2
        assert choices[0].delta.content == "Hello"
        assert choices[1].delta.content == " world"
