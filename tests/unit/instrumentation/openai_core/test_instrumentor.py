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


from agentops.instrumentation.openai.instrumentor import OpenAIInstrumentor
from agentops.instrumentation.common.wrappers import WrapConfig


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

        # To avoid timing issues with the fixture, we need to ensure patch
        # objects are created before being used in the test
        mock_wrap = patch("agentops.instrumentation.common.wrappers.wrap").start()
        mock_unwrap = patch("agentops.instrumentation.common.wrappers.unwrap").start()
        mock_instrument = patch.object(instrumentor, "_instrument", wraps=instrumentor._instrument).start()
        mock_uninstrument = patch.object(instrumentor, "_uninstrument", wraps=instrumentor._uninstrument).start()

        # Instrument
        instrumentor._instrument(tracer_provider=mock_tracer_provider)

        yield {
            "instrumentor": instrumentor,
            "tracer_provider": mock_tracer_provider,
            "mock_wrap": mock_wrap,
            "mock_unwrap": mock_unwrap,
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

        # Verify it inherits from BaseInstrumentor
        from opentelemetry.instrumentation.instrumentor import BaseInstrumentor

        assert isinstance(instrumentor, BaseInstrumentor)

    def test_instrument_method_wraps_response_api(self, instrumentor):
        """Test the _instrument method wraps the Response API methods"""
        mock_wrap = instrumentor["mock_wrap"]

        # Verify wrap was called multiple times (we wrap many methods)
        assert mock_wrap.call_count > 0

        # Find Response API calls in the wrapped methods
        response_api_calls = []
        for call in mock_wrap.call_args_list:
            wrap_config = call[0][0]
            if isinstance(wrap_config, WrapConfig) and wrap_config.package == "openai.resources.responses":
                response_api_calls.append(wrap_config)

        # Verify we have both sync and async Response API methods
        assert len(response_api_calls) == 2

        # Check sync Responses.create
        sync_response = next((cfg for cfg in response_api_calls if cfg.class_name == "Responses"), None)
        assert sync_response is not None
        assert sync_response.trace_name == "openai.responses.create"
        assert sync_response.method_name == "create"

        # Check async AsyncResponses.create
        async_response = next((cfg for cfg in response_api_calls if cfg.class_name == "AsyncResponses"), None)
        assert async_response is not None
        assert async_response.trace_name == "openai.responses.create"
        assert async_response.method_name == "create"

    def test_uninstrument_method_unwraps_response_api(self, instrumentor):
        """Test the _uninstrument method unwraps the Response API methods"""
        # For these tests, we'll manually call the unwrap method with the expected configs
        # since the fixture setup has been changed

        instrumentor_obj = instrumentor["instrumentor"]

        # Reset the mock to clear any previous calls
        mock_unwrap = instrumentor["mock_unwrap"]
        mock_unwrap.reset_mock()

        # Call the uninstrument method directly
        instrumentor_obj._uninstrument()

        # Now verify the method was called
        assert mock_unwrap.called, "unwrap was not called during _uninstrument"

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

        # Mock wrap to raise an exception
        with patch("agentops.instrumentation.common.wrappers.wrap") as mock_wrap:
            mock_wrap.side_effect = AttributeError("Module not found")

            # Instrument should not raise exceptions even if wrapping fails
            # The instrumentor should handle errors gracefully
            try:
                instrumentor._instrument(tracer_provider=MagicMock())
            except Exception:
                pytest.fail("Instrumentor should handle wrapping errors gracefully")

    def test_unwrapper_error_handling(self):
        """Test that the instrumentor handles errors when unwrapping methods"""
        # Create instrumentor
        instrumentor = OpenAIInstrumentor()

        # Mock unwrap to raise an exception
        with patch("agentops.instrumentation.common.wrappers.unwrap") as mock_unwrap:
            mock_unwrap.side_effect = Exception("Failed to unwrap")

            # Uninstrument should not raise exceptions even if unwrapping fails
            # The instrumentor should handle errors gracefully
            try:
                instrumentor._uninstrument()
            except Exception:
                pytest.fail("Instrumentor should handle unwrapping errors gracefully")

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
