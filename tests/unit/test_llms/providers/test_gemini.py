import os
import pytest
from unittest.mock import patch, MagicMock
from packaging.version import Version, parse

import google.generativeai as genai
import agentops
from agentops.llms.providers.gemini import GeminiProvider, _ORIGINAL_METHODS
from agentops.llms.tracker import LlmTracker
from agentops.event import LLMEvent, ErrorEvent

# Shared test utilities
class MockChunk:
    def __init__(self, text=None, finish_reason=None, usage_metadata=None, model=None, error=None):
        self._text = text
        self.finish_reason = finish_reason
        self.usage_metadata = usage_metadata
        self.model = model
        self._error = error

    @property
    def text(self):
        if self._error:
            raise self._error
        return self._text

    @text.setter
    def text(self, value):
        self._text = value


def test_gemini_provider_initialization():
    """Test GeminiProvider initialization and API key configuration."""
    # Test with valid model
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)
    assert provider.client == model
    assert provider.provider_name == "Gemini"
    assert "generate_content" not in _ORIGINAL_METHODS

    # Test API key configuration
    original_key = os.environ.get("GEMINI_API_KEY")
    try:
        # Test missing API key
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        provider.override()
        assert "generate_content" not in _ORIGINAL_METHODS

        # Test invalid API key
        os.environ["GEMINI_API_KEY"] = "invalid_key"
        provider.override()
        assert "generate_content" not in _ORIGINAL_METHODS

        # Test valid API key
        if original_key:
            os.environ["GEMINI_API_KEY"] = original_key
            provider.override()
            assert "generate_content" in _ORIGINAL_METHODS
    finally:
        if original_key:
            os.environ["GEMINI_API_KEY"] = original_key
        elif "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]


def test_gemini_version_checking():
    """Test version checking in LlmTracker for Gemini."""
    client = MagicMock()
    tracker = LlmTracker(client)

    with patch('agentops.llms.tracker.version') as mock_version, \
         patch('google.generativeai.GenerativeModel.generate_content') as mock_generate:
        # Test unsupported version
        mock_version.return_value = "0.0.9"
        tracker.override_api()
        assert "generate_content" not in _ORIGINAL_METHODS

        # Test minimum supported version
        mock_version.return_value = "0.1.0"
        tracker.override_api()
        assert "generate_content" in _ORIGINAL_METHODS

        # Test newer version
        mock_version.return_value = "0.2.0"
        tracker.override_api()
        assert "generate_content" in _ORIGINAL_METHODS

        # Test error handling
        mock_version.side_effect = Exception("Version error")
        tracker.override_api()
        assert "generate_content" not in _ORIGINAL_METHODS

        # Test missing package
        mock_version.side_effect = ModuleNotFoundError("Package not found")
        tracker.override_api()
        assert "generate_content" not in _ORIGINAL_METHODS


def test_gemini_sync_generation():
    """Test synchronous text generation with Gemini."""
    ao_client = agentops.init()
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)
    provider.override()

    try:
        # Create mock response class to simulate Gemini response
        class MockGeminiResponse:
            def __init__(self, text, model=None):
                self._text = text
                self._model = model

            @property
            def text(self):
                return self._text

            @property
            def model(self):
                return self._model

        # Test with default model value
        mock_response = MockGeminiResponse("Test response")
        result = provider.handle_response(mock_response, {"contents": "test"}, "2024-01-17T00:00:00Z", session=ao_client)
        assert isinstance(result, MockGeminiResponse)
        assert result.text == "Test response"
        assert getattr(result, "model", None) is None

        # Test with custom model value
        mock_response = MockGeminiResponse("Test response", model="custom-model")
        result = provider.handle_response(mock_response, {"contents": "test"}, "2024-01-17T00:00:00Z", session=ao_client)
        assert isinstance(result, MockGeminiResponse)
        assert result.model == "custom-model"

        # Test with missing prompt
        result = provider.handle_response(mock_response, {}, "2024-01-17T00:00:00Z", session=ao_client)
        assert isinstance(result, MockGeminiResponse)

        # Test with None prompt
        result = provider.handle_response(mock_response, {"contents": None}, "2024-01-17T00:00:00Z", session=ao_client)
        assert isinstance(result, MockGeminiResponse)

    finally:
        provider.undo_override()


def test_gemini_streaming():
    """Test streaming text generation with Gemini."""
    ao_client = agentops.init()
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)
    provider.override()

    try:
        # Test successful streaming
        chunks = [
            MockChunk("Hello", model=None),  # Test default model value
            MockChunk(" world", model="custom-model"),
            MockChunk("!", finish_reason="stop", model="custom-model")
        ]

        def mock_stream():
            for chunk in chunks:
                yield chunk

        result = provider.handle_response(
            mock_stream(), {"contents": "test", "stream": True}, "2024-01-17T00:00:00Z", session=ao_client
        )

        accumulated = []
        for chunk in result:
            accumulated.append(chunk.text)
        assert "".join(accumulated) == "Hello world!"

        # Test error handling in streaming
        error_chunks = [
            MockChunk("Start"),
            MockChunk(None, error=ValueError("Test error")),
            MockChunk("End", finish_reason="stop")
        ]

        def mock_error_stream():
            for chunk in error_chunks:
                yield chunk

        result = provider.handle_response(
            mock_error_stream(), {"contents": "test", "stream": True}, "2024-01-17T00:00:00Z", session=ao_client
        )

        accumulated = []
        for chunk in result:
            if hasattr(chunk, "text") and chunk.text:
                accumulated.append(chunk.text)
        assert "".join(accumulated) == "StartEnd"

    finally:
        provider.undo_override()


def test_gemini_error_handling():
    """Test error handling in GeminiProvider."""
    ao_client = agentops.init()
    provider = GeminiProvider(None)

    # Test initialization errors
    assert provider.client is None
    provider.override()  # Should handle None client gracefully

    # Test invalid client
    class InvalidClient:
        pass

    provider = GeminiProvider(InvalidClient())
    provider.override()  # Should handle invalid client gracefully

    # Test API configuration errors
    with patch('google.generativeai.configure') as mock_configure:
        mock_configure.side_effect = Exception("API config error")
        provider.override()
        assert "generate_content" not in _ORIGINAL_METHODS

    # Test response handling errors
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)

    # Test malformed response
    class MalformedResponse:
        @property
        def text(self):
            raise AttributeError("No text")

        @property
        def model(self):
            raise AttributeError("No model")

    result = provider.handle_response(
        MalformedResponse(), {"contents": "test"}, "2024-01-17T00:00:00Z", session=ao_client
    )
    assert isinstance(result, MalformedResponse)

    # Test streaming errors
    def error_generator():
        yield MockChunk("Before error")
        raise Exception("Stream error")
        yield MockChunk("After error")

    result = provider.handle_response(
        error_generator(), {"contents": "test", "stream": True}, "2024-01-17T00:00:00Z", session=ao_client
    )

    with pytest.raises(Exception, match="Stream error"):
        list(result)  # Force generator evaluation
