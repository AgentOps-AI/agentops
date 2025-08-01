"""Unit tests for LiteLLM instrumentation."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys

from agentops.instrumentation.providers.litellm import LiteLLMInstrumentor
from agentops.instrumentation.providers.litellm.callback_handler import AgentOpsLiteLLMCallback
from agentops.instrumentation.providers.litellm.utils import (
    detect_provider_from_model,
    extract_model_info,
    is_streaming_response,
    parse_litellm_error,
)
from agentops.instrumentation.providers.litellm.stream_wrapper import StreamWrapper, ChunkAggregator

# Mock litellm before importing our instrumentation
sys.modules["litellm"] = MagicMock()


class TestLiteLLMUtils(unittest.TestCase):
    """Test utility functions."""

    def test_detect_provider_from_model(self):
        """Test provider detection from model names."""
        test_cases = [
            ("gpt-4", "openai"),
            ("gpt-3.5-turbo", "openai"),
            ("claude-3-opus-20240229", "anthropic"),
            ("claude-2.1", "anthropic"),
            ("command-nightly", "cohere"),
            ("gemini-pro", "vertex_ai"),
            ("llama-2-70b", "unknown"),
            ("azure/gpt-4", "azure"),
            ("bedrock/anthropic.claude-v2", "bedrock"),
            ("unknown-model", "unknown"),
        ]

        for model, expected_provider in test_cases:
            with self.subTest(model=model):
                result = detect_provider_from_model(model)
                self.assertEqual(result, expected_provider)

    def test_extract_model_info(self):
        """Test model information extraction."""
        info = extract_model_info("gpt-4-turbo-32k")
        self.assertEqual(info["family"], "gpt-4")
        self.assertEqual(info["version"], "turbo")
        self.assertEqual(info["size"], "32k")

        info = extract_model_info("claude-3-opus")
        self.assertEqual(info["family"], "claude-3")
        self.assertEqual(info["version"], "opus")

    def test_is_streaming_response(self):
        """Test streaming response detection."""

        # Mock streaming response
        class MockStream:
            def __iter__(self):
                return self

            def __next__(self):
                raise StopIteration

        self.assertTrue(is_streaming_response(MockStream()))
        self.assertFalse(is_streaming_response({"choices": []}))
        self.assertFalse(is_streaming_response("not a stream"))

    def test_parse_litellm_error(self):
        """Test error parsing."""
        # Mock LiteLLM error
        error = Mock(spec=Exception)
        error.__class__.__name__ = "Exception"
        error.args = ("Rate limit exceeded",)
        error.status_code = 429
        error.llm_provider = "openai"

        parsed = parse_litellm_error(error)
        self.assertEqual(parsed["type"], "Exception")
        self.assertEqual(parsed["error_category"], "rate_limit")
        self.assertEqual(parsed["status_code"], 429)
        self.assertEqual(parsed["llm_provider"], "openai")


class TestChunkAggregator(unittest.TestCase):
    """Test chunk aggregation for streaming."""

    def test_aggregate_content(self):
        """Test aggregating content from chunks."""
        aggregator = ChunkAggregator()

        # Mock chunks
        chunks = [
            Mock(choices=[Mock(delta=Mock(content="Hello"))]),
            Mock(choices=[Mock(delta=Mock(content=" world"))]),
            Mock(choices=[Mock(delta=Mock(content="!"))]),
        ]

        for chunk in chunks:
            aggregator.add_chunk(chunk)

        self.assertEqual(aggregator.get_aggregated_content(), "Hello world!")

    def test_aggregate_function_calls(self):
        """Test aggregating function calls from chunks."""
        aggregator = ChunkAggregator()

        # Mock chunks with function call
        chunks = [
            Mock(choices=[Mock(delta=Mock(function_call=Mock(arguments='{"location":')))]),
            Mock(choices=[Mock(delta=Mock(function_call=Mock(arguments=' "San Francisco"}')))]),
        ]

        for chunk in chunks:
            aggregator.add_chunk(chunk)

        self.assertEqual(aggregator.get_aggregated_function_call(), '{"location": "San Francisco"}')


class TestCallbackHandler(unittest.TestCase):
    """Test the callback handler."""

    def setUp(self):
        """Set up test fixtures."""
        self.instrumentor = Mock()
        self.handler = AgentOpsLiteLLMCallback(self.instrumentor)

    @patch("agentops.instrumentation.providers.litellm.callback_handler.trace")
    def test_log_pre_api_call(self, mock_trace):
        """Test pre-API call logging."""
        mock_span = Mock()
        mock_trace.get_current_span.return_value = mock_span
        mock_span.is_recording.return_value = True

        messages = [{"role": "system", "content": "You are helpful"}, {"role": "user", "content": "Hello"}]
        kwargs = {"temperature": 0.7, "max_tokens": 100, "litellm_call_id": "test-123"}

        self.handler.log_pre_api_call("gpt-3.5-turbo", messages, kwargs)

        # Verify span attributes were set
        mock_span.set_attribute.assert_any_call("llm.vendor", "litellm")
        mock_span.set_attribute.assert_any_call("llm.request.model", "gpt-3.5-turbo")
        mock_span.set_attribute.assert_any_call("llm.request.messages_count", 2)
        mock_span.set_attribute.assert_any_call("llm.request.temperature", 0.7)
        mock_span.set_attribute.assert_any_call("llm.request.max_tokens", 100)

    @patch("agentops.instrumentation.providers.litellm.callback_handler.trace")
    def test_log_success_event(self, mock_trace):
        """Test success event logging."""
        mock_span = Mock()
        mock_trace.get_current_span.return_value = mock_span
        mock_span.is_recording.return_value = True

        # Mock response
        response = Mock()
        response.id = "chatcmpl-123"
        response.model = "gpt-3.5-turbo-0613"
        response.choices = [Mock(message=Mock(content="Hello there!"), finish_reason="stop")]
        response.usage = Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        kwargs = {"litellm_call_id": "test-123"}

        self.handler.log_success_event(kwargs, response, 1.0, 2.0)

        # Verify response attributes
        mock_span.set_attribute.assert_any_call("llm.response.duration_seconds", 1.0)
        mock_span.set_attribute.assert_any_call("llm.response.id", "chatcmpl-123")
        mock_span.set_attribute.assert_any_call("llm.response.choices_count", 1)
        mock_span.set_attribute.assert_any_call("llm.usage.prompt_tokens", 10)
        mock_span.set_attribute.assert_any_call("llm.usage.completion_tokens", 5)
        mock_span.set_attribute.assert_any_call("llm.usage.total_tokens", 15)


class TestStreamWrapper(unittest.TestCase):
    """Test stream wrapper functionality."""

    def test_stream_wrapper_basic(self):
        """Test basic stream wrapper functionality."""
        # Mock stream
        chunks = ["chunk1", "chunk2", "chunk3"]
        mock_stream = iter(chunks)

        # Mock span
        mock_span = Mock()

        # Create wrapper
        wrapper = StreamWrapper(mock_stream, mock_span)

        # Consume stream
        collected = list(wrapper)

        self.assertEqual(collected, chunks)
        self.assertEqual(len(wrapper.chunks), 3)

        # Verify time to first token was set
        mock_span.set_attribute.assert_any_call("llm.response.time_to_first_token", wrapper.first_chunk_time)


class TestLiteLLMInstrumentor(unittest.TestCase):
    """Test the main instrumentor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.instrumentor = LiteLLMInstrumentor()

    @patch("agentops.instrumentation.providers.litellm.instrumentor.logger")
    def test_instrument_not_available(self, mock_logger):
        """Test instrumentation when LiteLLM is not available."""
        with patch.object(self.instrumentor, "_check_library_available", return_value=False):
            result = self.instrumentor.instrument()
            self.assertFalse(result)

    @patch("sys.modules", {"litellm": Mock()})
    def test_register_callbacks(self):
        """Test callback registration."""
        mock_litellm = Mock()
        mock_litellm.success_callback = None
        mock_litellm.failure_callback = None
        mock_litellm.start_callback = None

        self.instrumentor._register_callbacks(mock_litellm)

        # Verify callbacks were registered
        self.assertIn("agentops", mock_litellm.success_callback)
        self.assertIn("agentops", mock_litellm.failure_callback)
        self.assertIn("agentops", mock_litellm.start_callback)


if __name__ == "__main__":
    unittest.main()
