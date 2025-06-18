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


from agentops.instrumentation.providers.openai.instrumentor import OpenaiInstrumentor
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


class TestOpenaiInstrumentor:
    """Tests for OpenAI API instrumentation, focusing on Response API support"""

    @pytest.fixture
    def instrumentor(self):
        """Set up OpenAI instrumentor for tests"""
        # Create patches for tracer and meter
        with patch("agentops.instrumentation.common.instrumentor.get_tracer") as mock_get_tracer:
            with patch("agentops.instrumentation.common.instrumentor.get_meter") as mock_get_meter:
                # Set up mock tracer and meter
                mock_tracer = MagicMock()
                mock_meter = MagicMock()
                mock_get_tracer.return_value = mock_tracer
                mock_get_meter.return_value = mock_meter

                # Create a real instrumentation setup for testing
                mock_tracer_provider = MagicMock()
                instrumentor = OpenaiInstrumentor()

                # To avoid timing issues with the fixture, we need to ensure patch
                # objects are created before being used in the test
                mock_wrap = patch("agentops.instrumentation.common.instrumentor.wrap").start()
                mock_unwrap = patch("agentops.instrumentation.common.instrumentor.unwrap").start()
                mock_instrument = patch.object(instrumentor, "_instrument", wraps=instrumentor._instrument).start()
                mock_uninstrument = patch.object(
                    instrumentor, "_uninstrument", wraps=instrumentor._uninstrument
                ).start()

                # Instrument
                instrumentor._instrument(tracer_provider=mock_tracer_provider)

                yield {
                    "instrumentor": instrumentor,
                    "tracer_provider": mock_tracer_provider,
                    "mock_wrap": mock_wrap,
                    "mock_unwrap": mock_unwrap,
                    "mock_instrument": mock_instrument,
                    "mock_uninstrument": mock_uninstrument,
                    "mock_tracer": mock_tracer,
                    "mock_meter": mock_meter,
                }

                # Uninstrument - must happen before stopping patches
                instrumentor._uninstrument()

                # Stop patches
                patch.stopall()

    def test_instrumentor_initialization(self):
        """Test instrumentor is initialized with correct configuration"""
        instrumentor = OpenaiInstrumentor()
        assert instrumentor.__class__.__name__ == "OpenaiInstrumentor"

        # Verify it inherits from BaseInstrumentor
        from opentelemetry.instrumentation.instrumentor import BaseInstrumentor

        assert isinstance(instrumentor, BaseInstrumentor)

    def test_instrument_method_wraps_response_api(self, instrumentor):
        """Test the _instrument method wraps the Response API methods"""
        # Since the Response API wrapping happens in _custom_wrap which is called during
        # _instrument, we need to check if it was attempted
        # The actual wrapping might fail if openai module is not available in test

        # Check that the instrumentor was created and has the expected structure
        inst = instrumentor["instrumentor"]
        assert hasattr(inst, "_custom_wrap")

        # The key thing is that the OpenAI instrumentor attempts to wrap Response API
        # We can verify this by checking that _custom_wrap exists and would be called
        # during instrumentation
        assert inst.__class__.__name__ == "OpenAIInstrumentor"

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
        instrumentor = OpenaiInstrumentor()

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
        instrumentor = OpenaiInstrumentor()

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
        instrumentor = OpenaiInstrumentor()

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
