"""
Tests for OpenAI API Custom Wrappers

This module contains tests for the custom wrappers used in the OpenAI instrumentor.
It verifies that our custom wrappers correctly handle context from OpenAI Agents SDK
and set the appropriate attributes on spans.
"""

import pytest
from unittest.mock import MagicMock, patch

from opentelemetry import context as context_api
from opentelemetry.trace import SpanKind, StatusCode

from agentops.instrumentation.openai.instrumentor import (
    OpenAIInstrumentor,
    responses_wrapper,
    async_responses_wrapper,
)


class TestOpenAICustomWrappers:
    """Tests for OpenAI API custom wrappers"""

    @pytest.fixture
    def mock_tracer(self):
        """Set up a mock tracer for testing"""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        return mock_tracer, mock_span

    @pytest.fixture
    def mock_context(self):
        """Set up a mock context with OpenAI Agents SDK trace information"""
        # Mock the context_api.get_value method to return our test values
        with patch.object(context_api, "get_value") as mock_get_value:
            # Set up the mock to return different values based on the key
            def side_effect(key, default=None, context=None):
                if key == "openai_agents.trace_id":
                    return "test-trace-id"
                elif key == "openai_agents.parent_id":
                    return "test-parent-id"
                elif key == "openai_agents.workflow_input":
                    return "test workflow input"
                elif key == "suppress_instrumentation":
                    return False
                return default

            mock_get_value.side_effect = side_effect
            yield mock_get_value

    def test_responses_wrapper_with_context(self, mock_tracer, mock_context):
        """Test that the responses_wrapper correctly handles context from OpenAI Agents SDK"""
        mock_tracer, mock_span = mock_tracer

        # Create a mock wrapped function
        mock_wrapped = MagicMock()
        mock_wrapped.return_value = {"id": "test-response-id", "model": "test-model"}

        # Set up mock get_response_attributes to return empty dict
        with patch("agentops.instrumentation.openai.instrumentor.get_response_attributes", return_value={}):
            # Call the wrapper
            result = responses_wrapper(mock_tracer, mock_wrapped, None, [], {})

            # Verify the wrapped function was called
            assert mock_wrapped.called

            # Verify the span was created with the correct name and kind
            mock_tracer.start_as_current_span.assert_called_once_with(
                "openai.responses.create",
                kind=SpanKind.CLIENT,
            )

            # Verify the context attributes were set on the span
            mock_span.set_attribute.assert_any_call("openai_agents.trace_id", "test-trace-id")
            mock_span.set_attribute.assert_any_call("openai_agents.parent_id", "test-parent-id")
            mock_span.set_attribute.assert_any_call("workflow.input", "test workflow input")

            # Verify the status was set to OK
            # Use assert_called to check that set_status was called, then check the status code
            assert mock_span.set_status.called, "set_status was not called"
            status_arg = mock_span.set_status.call_args[0][0]
            assert status_arg.status_code == StatusCode.OK, f"Expected status code OK, got {status_arg.status_code}"

            # Verify the result was returned
            assert result == {"id": "test-response-id", "model": "test-model"}

    @pytest.mark.asyncio
    async def test_async_responses_wrapper_with_context(self, mock_tracer, mock_context):
        """Test that the async_responses_wrapper correctly handles context from OpenAI Agents SDK"""
        mock_tracer, mock_span = mock_tracer

        # Create a mock wrapped function that returns a coroutine
        async def mock_async_func(*args, **kwargs):
            return {"id": "test-response-id", "model": "test-model"}

        mock_wrapped = MagicMock()
        mock_wrapped.side_effect = mock_async_func

        # Set up mock get_response_attributes to return empty dict
        with patch("agentops.instrumentation.openai.instrumentor.get_response_attributes", return_value={}):
            # Call the wrapper
            result = await async_responses_wrapper(mock_tracer, mock_wrapped, None, [], {})

            # Verify the wrapped function was called
            assert mock_wrapped.called

            # Verify the span was created with the correct name and kind
            mock_tracer.start_as_current_span.assert_called_once_with(
                "openai.responses.create",
                kind=SpanKind.CLIENT,
            )

            # Verify the context attributes were set on the span
            mock_span.set_attribute.assert_any_call("openai_agents.trace_id", "test-trace-id")
            mock_span.set_attribute.assert_any_call("openai_agents.parent_id", "test-parent-id")
            mock_span.set_attribute.assert_any_call("workflow.input", "test workflow input")

            # Verify the status was set to OK
            # Use assert_called to check that set_status was called, then check the status code
            assert mock_span.set_status.called, "set_status was not called"
            status_arg = mock_span.set_status.call_args[0][0]
            assert status_arg.status_code == StatusCode.OK, f"Expected status code OK, got {status_arg.status_code}"

            # Verify the result was returned
            assert result == {"id": "test-response-id", "model": "test-model"}

    def test_instrumentor_uses_custom_wrappers(self):
        """Test that the instrumentor uses the custom wrappers"""
        # Create instrumentor
        instrumentor = OpenAIInstrumentor()

        # Mock wrap_function_wrapper
        with patch("wrapt.wrap_function_wrapper") as mock_wrap_function_wrapper:
            # Mock wrap to avoid errors
            with patch("agentops.instrumentation.openai.instrumentor.wrap"):
                # Mock the parent class's _instrument method to do nothing
                with patch.object(instrumentor.__class__.__bases__[0], "_instrument"):
                    # Instrument
                    instrumentor._instrument(tracer_provider=MagicMock())

                    # Verify wrap_function_wrapper was called for both methods
                    assert mock_wrap_function_wrapper.call_count == 2

                    # Check the first call arguments for Responses.create
                    first_call_args = mock_wrap_function_wrapper.call_args_list[0]
                    assert first_call_args[0][0] == "openai.resources.responses"
                    assert first_call_args[0][1] == "Responses.create"

                    # Check the second call arguments for AsyncResponses.create
                    second_call_args = mock_wrap_function_wrapper.call_args_list[1]
                    assert second_call_args[0][0] == "openai.resources.responses"
                    assert second_call_args[0][1] == "AsyncResponses.create"

    def test_instrumentor_unwraps_custom_wrappers(self):
        """Test that the instrumentor unwraps the custom wrappers"""
        # Create instrumentor
        instrumentor = OpenAIInstrumentor()

        # Mock unwrap
        with patch("opentelemetry.instrumentation.utils.unwrap") as mock_unwrap:
            # Mock standard unwrap to avoid errors
            with patch("agentops.instrumentation.openai.instrumentor.unwrap"):
                # Mock the parent class's _uninstrument method to do nothing
                with patch.object(instrumentor.__class__.__bases__[0], "_uninstrument"):
                    # Uninstrument
                    instrumentor._uninstrument()

                    # Verify unwrap was called for both methods
                    assert mock_unwrap.call_count == 2

                    # Check the first call arguments for Responses.create
                    first_call_args = mock_unwrap.call_args_list[0]
                    assert first_call_args[0][0] == "openai.resources.responses.Responses"
                    assert first_call_args[0][1] == "create"

                    # Check the second call arguments for AsyncResponses.create
                    second_call_args = mock_unwrap.call_args_list[1]
                    assert second_call_args[0][0] == "openai.resources.responses.AsyncResponses"
                    assert second_call_args[0][1] == "create"
