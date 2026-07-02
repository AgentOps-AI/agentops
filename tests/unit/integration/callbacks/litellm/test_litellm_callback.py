"""
Tests for LiteLLM callback handler.

Tests the LiteLLMCallbackHandler for proper span creation, attribute extraction,
and handling of both completion and responses API calls.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from agentops.integration.callbacks.litellm.callback import LiteLLMCallbackHandler
from agentops.semconv import SpanAttributes, AgentOpsSpanKindValues


class TestLiteLLMCallbackHandler:
    """Tests for the LiteLLM callback handler."""

    @pytest.fixture
    def mock_tracer(self):
        """Mock the tracer for testing."""
        with patch("agentops.integration.callbacks.litellm.callback.tracer") as mock:
            mock.initialized = True
            mock_otel_tracer = MagicMock()
            mock.get_tracer.return_value = mock_otel_tracer
            yield mock

    @pytest.fixture
    def handler(self, mock_tracer):
        """Create a handler with mocked dependencies."""
        with patch("agentops.integration.callbacks.litellm.callback.tracer", mock_tracer):
            handler = LiteLLMCallbackHandler(auto_session=False)
            yield handler

    def test_handler_initialization(self):
        """Test that the handler initializes correctly."""
        with patch("agentops.integration.callbacks.litellm.callback.tracer") as mock_tracer:
            mock_tracer.initialized = False
            
            handler = LiteLLMCallbackHandler(
                api_key="test-key",
                tags=["test-tag"],
                auto_session=False,
            )
            
            assert handler.api_key == "test-key"
            assert handler.tags == ["test-tag"]
            assert handler.active_spans == {}
            assert handler.context_tokens == {}

    def test_extract_provider_from_model_string(self, handler):
        """Test provider extraction from model strings."""
        assert handler._extract_provider("anthropic/claude-3-5-sonnet-20240620") == "anthropic"
        assert handler._extract_provider("openai/gpt-4o") == "openai"
        assert handler._extract_provider("google/gemini-pro") == "google"
        assert handler._extract_provider("gpt-4o") == "openai"
        assert handler._extract_provider("claude-3-sonnet") == "anthropic"
        assert handler._extract_provider("gemini-pro") == "google"
        assert handler._extract_provider("mixtral-8x7b") == "mistral"
        assert handler._extract_provider("command-r") == "cohere"
        assert handler._extract_provider("unknown-model") == "unknown"

    def test_get_call_id(self, handler):
        """Test call ID generation."""
        # With litellm_call_id
        kwargs_with_id = {"litellm_call_id": "test-call-123"}
        assert handler._get_call_id(kwargs_with_id) == "test-call-123"
        
        # Without litellm_call_id (fallback)
        kwargs_without_id = {"model": "gpt-4"}
        call_id = handler._get_call_id(kwargs_without_id)
        assert "gpt-4" in call_id

    def test_log_pre_api_call_creates_span(self, handler, mock_tracer):
        """Test that log_pre_api_call creates a span."""
        mock_span = MagicMock()
        mock_tracer.get_tracer().start_span.return_value = mock_span
        
        model = "anthropic/claude-3-5-sonnet-20240620"
        messages = [{"role": "user", "content": "Hello"}]
        kwargs = {"litellm_call_id": "test-123", "temperature": 0.7}
        
        handler.log_pre_api_call(model, messages, kwargs)
        
        # Verify span was created and stored
        assert "test-123" in handler.active_spans
        mock_tracer.get_tracer().start_span.assert_called_once()

    def test_log_success_event_ends_span(self, handler, mock_tracer):
        """Test that log_success_event ends the span correctly."""
        mock_span = MagicMock()
        mock_tracer.get_tracer().start_span.return_value = mock_span
        
        # First create a span
        model = "gpt-4o"
        messages = [{"role": "user", "content": "Hello"}]
        kwargs = {"litellm_call_id": "test-123"}
        
        handler.log_pre_api_call(model, messages, kwargs)
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.model = "gpt-4o"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_response.choices = [
            MagicMock(
                message=MagicMock(role="assistant", content="Hi there!"),
                finish_reason="stop"
            )
        ]
        
        # Now end the span
        handler.log_success_event(
            kwargs,
            mock_response,
            datetime.now(),
            datetime.now(),
        )
        
        # Verify span was ended
        assert "test-123" not in handler.active_spans
        mock_span.end.assert_called_once()

    def test_log_failure_event_records_exception(self, handler, mock_tracer):
        """Test that log_failure_event records the exception."""
        mock_span = MagicMock()
        mock_tracer.get_tracer().start_span.return_value = mock_span
        
        # First create a span
        model = "gpt-4o"
        messages = [{"role": "user", "content": "Hello"}]
        kwargs = {"litellm_call_id": "test-123"}
        
        handler.log_pre_api_call(model, messages, kwargs)
        
        # Create exception
        test_exception = ValueError("API Error")
        kwargs["exception"] = test_exception
        
        # Now handle failure
        handler.log_failure_event(
            kwargs,
            None,
            datetime.now(),
            datetime.now(),
        )
        
        # Verify exception was recorded
        mock_span.record_exception.assert_called_once_with(test_exception)

    def test_handles_responses_api_format(self, handler, mock_tracer):
        """Test handling of responses API format (output instead of choices)."""
        mock_span = MagicMock()
        mock_tracer.get_tracer().start_span.return_value = mock_span
        
        # Create a span
        model = "gpt-4o"
        messages = [{"role": "user", "content": "Hello"}]
        kwargs = {"litellm_call_id": "test-123"}
        
        handler.log_pre_api_call(model, messages, kwargs)
        
        # Create responses API format response
        mock_response = MagicMock()
        mock_response.model = "gpt-4o"
        mock_response.usage = {"input_tokens": 10, "output_tokens": 20}
        mock_response.choices = None
        mock_response.output = [
            {"content": [{"type": "text", "text": "Hello from responses API!"}]}
        ]
        
        handler.log_success_event(
            kwargs,
            mock_response,
            datetime.now(),
            datetime.now(),
        )
        
        # Verify span attributes were set
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.LLM_USAGE_PROMPT_TOKENS, 10
        )
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, 20
        )

    def test_handles_anthropic_model(self, handler, mock_tracer):
        """Test that Anthropic models are properly handled."""
        mock_span = MagicMock()
        mock_tracer.get_tracer().start_span.return_value = mock_span
        
        model = "anthropic/claude-3-5-sonnet-20240620"
        messages = [{"role": "user", "content": "Hello"}]
        kwargs = {"litellm_call_id": "test-123"}
        
        handler.log_pre_api_call(model, messages, kwargs)
        
        # Verify provider was extracted correctly
        call_args = mock_tracer.get_tracer().start_span.call_args
        attributes = call_args[1].get("attributes", {})
        
        assert attributes.get("litellm.provider") == "anthropic"
        assert attributes.get("gen_ai.system") == "anthropic"

    def test_handles_openai_model(self, handler, mock_tracer):
        """Test that OpenAI models are properly handled."""
        mock_span = MagicMock()
        mock_tracer.get_tracer().start_span.return_value = mock_span
        
        model = "gpt-4o"
        messages = [{"role": "user", "content": "Hello"}]
        kwargs = {"litellm_call_id": "test-123"}
        
        handler.log_pre_api_call(model, messages, kwargs)
        
        # Verify provider was extracted correctly
        call_args = mock_tracer.get_tracer().start_span.call_args
        attributes = call_args[1].get("attributes", {})
        
        assert attributes.get("litellm.provider") == "openai"
        assert attributes.get("gen_ai.system") == "openai"

    def test_end_session_cleans_up(self, handler, mock_tracer):
        """Test that end_session properly cleans up resources."""
        mock_span = MagicMock()
        mock_tracer.get_tracer().start_span.return_value = mock_span
        
        # Create some spans
        handler.log_pre_api_call("gpt-4", [], {"litellm_call_id": "test-1"})
        handler.log_pre_api_call("gpt-4", [], {"litellm_call_id": "test-2"})
        
        assert len(handler.active_spans) == 2
        
        # End session
        handler.end_session()
        
        # Verify cleanup
        assert len(handler.active_spans) == 0
        assert len(handler.context_tokens) == 0


class TestLiteLLMCallbackIntegration:
    """Integration-style tests for LiteLLM callback handler."""

    def test_callback_handler_can_be_imported(self):
        """Test that the callback handler can be imported from agentops."""
        from agentops import LiteLLMCallbackHandler
        
        assert LiteLLMCallbackHandler is not None

    def test_callback_inherits_from_custom_logger(self):
        """Test that the callback handler inherits from CustomLogger if available."""
        try:
            from litellm.integrations.custom_logger import CustomLogger
            from agentops.integration.callbacks.litellm.callback import LiteLLMCallbackHandler
            
            # Should inherit from CustomLogger
            assert issubclass(LiteLLMCallbackHandler, CustomLogger)
        except ImportError:
            # LiteLLM not installed, skip this test
            pytest.skip("LiteLLM not installed")
