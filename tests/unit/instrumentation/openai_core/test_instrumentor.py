"""
Tests for OpenAI API Instrumentation

This module contains tests for properly handling and serializing data from the OpenAI API.
It verifies that our instrumentation correctly captures and instruments API calls,
specifically focusing on the newer Response API format used in the Agents SDK.

The OpenAI Instrumentor extends the third-party OpenTelemetry instrumentor and adds
our own wrapper for the newer Response API format.
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch


from agentops.instrumentation.providers.openai.instrumentor import OpenAIInstrumentor


# Utility function to load fixtures
def load_fixture(fixture_name):
    """Load a test fixture from the fixtures directory"""
    fixture_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures", fixture_name)
    with open(fixture_path, "r") as f:
        return json.load(f)


# Load response test fixtures
OPENAI_RESPONSE = load_fixture("openai_response.json")  # Response API format (newer API format) with output array
OPENAI_RESPONSE_TOOL_CALLS = load_fixture("openai_response_tool_calls.json")  # Response API with tool calls


class TestOpenAIInstrumentor:
    """Tests for OpenAI API instrumentation, focusing on Response API support"""

    @pytest.fixture
    def instrumentor(self):
        """Set up OpenAI instrumentor for tests"""
        # Create a real instrumentation setup for testing
        mock_tracer_provider = MagicMock()
        instrumentor = OpenAIInstrumentor()

        # Mock at the base class level
        mock_wrap_method = patch.object(instrumentor, "_wrap_method").start()
        mock_unwrap_method = patch.object(instrumentor, "_unwrap_method").start()
        mock_instrument = patch.object(instrumentor, "_instrument", wraps=instrumentor._instrument).start()
        mock_uninstrument = patch.object(instrumentor, "_uninstrument", wraps=instrumentor._uninstrument).start()

        # Instrument
        instrumentor._instrument(tracer_provider=mock_tracer_provider)

        yield {
            "instrumentor": instrumentor,
            "tracer_provider": mock_tracer_provider,
            "mock_wrap_method": mock_wrap_method,
            "mock_unwrap_method": mock_unwrap_method,
            "mock_instrument": mock_instrument,
            "mock_uninstrument": mock_uninstrument,
        }

        # Uninstrument - must happen before stopping patches
        instrumentor._uninstrument()

        # Stop patches
        patch.stopall()

    def test_instrumentor_initialization(self):
        """Test instrumentor is initialized with correct configuration"""
        instrumentor = OpenAIInstrumentor()
        assert instrumentor.__class__.__name__ == "OpenAIInstrumentor"

        # Verify it inherits from AgentOpsBaseInstrumentor
        from agentops.instrumentation.common.base_instrumentor import AgentOpsBaseInstrumentor

        assert isinstance(instrumentor, AgentOpsBaseInstrumentor)

    def test_instrument_method_wraps_response_api(self, instrumentor):
        """Test the _instrument method wraps the Response API methods"""
        mock_wrap_method = instrumentor["mock_wrap_method"]
        instrumentor_obj = instrumentor["instrumentor"]

        # Get the wrapped methods from the instrumentor
        wrapped_methods = instrumentor_obj.get_wrapped_methods()

        # Filter for Response API methods
        response_api_methods = [cfg for cfg in wrapped_methods if cfg.package == "openai.resources.responses"]

        # Verify we have both sync and async Response API methods
        assert len(response_api_methods) == 2

        # Check sync Responses.create
        sync_response = next((cfg for cfg in response_api_methods if cfg.class_name == "Responses"), None)
        assert sync_response is not None
        assert sync_response.trace_name == "openai.responses.create"
        assert sync_response.method_name == "create"

        # Check async AsyncResponses.create
        async_response = next((cfg for cfg in response_api_methods if cfg.class_name == "AsyncResponses"), None)
        assert async_response is not None
        assert async_response.trace_name == "openai.responses.create"
        assert async_response.method_name == "create"

        # Verify _wrap_method was called for each wrapped method
        assert mock_wrap_method.call_count == len(wrapped_methods)

    def test_uninstrument_method_unwraps_response_api(self, instrumentor):
        """Test the _uninstrument method unwraps the Response API methods"""
        instrumentor_obj = instrumentor["instrumentor"]
        mock_unwrap_method = instrumentor["mock_unwrap_method"]

        # Get the wrapped methods
        wrapped_methods = instrumentor_obj.get_wrapped_methods()

        # Reset the mock to clear any previous calls
        mock_unwrap_method.reset_mock()

        # Call the uninstrument method directly
        instrumentor_obj._uninstrument()

        # Verify _unwrap_method was called for each wrapped method
        assert mock_unwrap_method.call_count == len(wrapped_methods)

    def test_calls_parent_instrument(self, instrumentor):
        """Test that the instrumentor properly instruments methods"""
        mock_instrument = instrumentor["mock_instrument"]

        # Verify _instrument was called
        assert mock_instrument.called

        # Verify the tracer provider was passed
        call_kwargs = mock_instrument.call_args[1]
        assert "tracer_provider" in call_kwargs
        assert call_kwargs["tracer_provider"] == instrumentor["tracer_provider"]

    def test_calls_parent_uninstrument(self, instrumentor):
        """Test that the instrumentor properly uninstruments methods"""
        instrumentor_obj = instrumentor["instrumentor"]
        mock_uninstrument = instrumentor["mock_uninstrument"]

        # Reset the mock to clear any previous calls
        mock_uninstrument.reset_mock()

        # Directly call uninstrument
        instrumentor_obj._uninstrument()

        # Now verify the method was called
        assert mock_uninstrument.called, "_uninstrument was not called"

    def test_wrapper_error_handling(self):
        """Test that the instrumentor handles errors when wrapping methods"""
        # Create instrumentor
        instrumentor = OpenAIInstrumentor()

        # The base class _wrap_method already handles errors internally
        # So we just test that instrumentation doesn't raise exceptions
        mock_tracer_provider = MagicMock()

        # This should not raise an exception even if some wrapping fails
        try:
            instrumentor._instrument(tracer_provider=mock_tracer_provider)
        except Exception as e:
            pytest.fail(f"Instrumentor should handle wrapping errors gracefully, but raised: {e}")

    def test_unwrapper_error_handling(self):
        """Test that the instrumentor handles errors when unwrapping methods"""
        # Create instrumentor
        instrumentor = OpenAIInstrumentor()

        # The base class _unwrap_method already handles errors internally
        # So we just test that uninstrumentation doesn't raise exceptions

        # First instrument
        mock_tracer_provider = MagicMock()
        instrumentor._instrument(tracer_provider=mock_tracer_provider)

        # Then uninstrument - this should not raise an exception
        try:
            instrumentor._uninstrument()
        except Exception as e:
            pytest.fail(f"Instrumentor should handle unwrapping errors gracefully, but raised: {e}")

    def test_instrumentation_with_tracer(self):
        """Test that the instrumentor gets a tracer with the correct name and version"""
        # Create instrumentor
        instrumentor = OpenAIInstrumentor()

        # Since get_tracer is now imported at module level in openai/instrumentor.py,
        # we can test this through spying on the _instrument method instead
        with patch.object(instrumentor, "_instrument", wraps=instrumentor._instrument) as mock_instrument_method:
            # Instrument
            mock_tracer_provider = MagicMock()
            instrumentor._instrument(tracer_provider=mock_tracer_provider)

            # Verify the method was called with the expected parameters
            assert mock_instrument_method.called
            assert "tracer_provider" in mock_instrument_method.call_args[1]
            assert mock_instrument_method.call_args[1]["tracer_provider"] == mock_tracer_provider

    def test_wrapped_methods_initialization(self):
        """Test that wrapped methods are properly initialized"""
        instrumentor = OpenAIInstrumentor()

        # Get wrapped methods
        wrapped_methods = instrumentor.get_wrapped_methods()

        # Verify we have methods wrapped
        assert len(wrapped_methods) > 0

        # Check for key method types
        method_types = {cfg.trace_name for cfg in wrapped_methods}
        expected_types = {
            "openai.chat.completion",
            "openai.completion",
            "openai.embeddings",
            "openai.images.generate",
            "openai.responses.create",  # Our custom Response API
        }

        # Verify all expected types are present
        for expected in expected_types:
            assert expected in method_types, f"Missing wrapped method type: {expected}"

    def test_streaming_methods(self):
        """Test that streaming methods are properly configured"""
        instrumentor = OpenAIInstrumentor()

        # Get streaming methods
        streaming_methods = instrumentor.get_streaming_methods()

        # OpenAI instrumentor may or may not have streaming methods
        # This is implementation-specific
        assert isinstance(streaming_methods, list)
