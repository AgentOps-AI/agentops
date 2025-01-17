import google.generativeai as genai
import agentops
from agentops.llms.providers.gemini import GeminiProvider

# Configure the API key from environment variable
import os
import pytest

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")
genai.configure(api_key=GEMINI_API_KEY)


def test_gemini_provider():
    """Test GeminiProvider initialization and override."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)
    assert provider.client == model
    assert provider.provider_name == "Gemini"
    assert provider.original_generate is None


def test_gemini_sync_generation():
    """Test synchronous text generation with Gemini."""
    ao_client = agentops.init()
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)
    provider.override()

    try:
        response = model.generate_content("What is artificial intelligence?", session=ao_client)
        assert response is not None
        assert hasattr(response, "text")
        assert isinstance(response.text, str)
        assert len(response.text) > 0
    finally:
        provider.undo_override()


def test_gemini_streaming():
    """Test streaming text generation with Gemini."""
    ao_client = agentops.init()
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)
    provider.override()

    try:
        response = model.generate_content("Explain quantum computing", stream=True, session=ao_client)
        accumulated_text = []
        for chunk in response:
            assert hasattr(chunk, "text")
            accumulated_text.append(chunk.text)
        assert len(accumulated_text) > 0
        assert "".join(accumulated_text)
    finally:
        provider.undo_override()


def test_gemini_error_handling():
    """Test error handling in GeminiProvider."""
    provider = GeminiProvider(None)
    assert provider.client is None

    # Should not raise exception but log warning
    provider.override()
    provider.undo_override()


def test_gemini_handle_response():
    """Test handle_response method with various scenarios."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)
    ao_client = agentops.init()

    # Test handling response with usage metadata
    class MockResponse:
        def __init__(self, text, usage_metadata=None):
            self.text = text
            self.usage_metadata = usage_metadata

    response = MockResponse(
        "Test response",
        usage_metadata=type("UsageMetadata", (), {"prompt_token_count": 10, "candidates_token_count": 20}),
    )

    result = provider.handle_response(response, {"contents": "Test prompt"}, "2024-01-17T00:00:00Z", session=ao_client)
    assert result == response


def test_gemini_streaming_chunks():
    """Test streaming response handling with chunks."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)
    ao_client = agentops.init()

    # Mock streaming chunks
    class MockChunk:
        def __init__(self, text, finish_reason=None, usage_metadata=None):
            self.text = text
            self.finish_reason = finish_reason
            self.usage_metadata = usage_metadata

    chunks = [
        MockChunk("Hello"),
        MockChunk(
            " world", usage_metadata=type("UsageMetadata", (), {"prompt_token_count": 5, "candidates_token_count": 10})
        ),
        MockChunk("!", finish_reason="stop"),
    ]

    def mock_stream():
        for chunk in chunks:
            yield chunk

    result = provider.handle_response(
        mock_stream(), {"contents": "Test prompt", "stream": True}, "2024-01-17T00:00:00Z", session=ao_client
    )

    # Verify streaming response
    accumulated = []
    for chunk in result:
        accumulated.append(chunk.text)
    assert "".join(accumulated) == "Hello world!"


def test_undo_override():
    """Test undo_override functionality."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)

    # Store original method
    original_generate = model.generate_content

    # Override and verify
    provider.override()
    assert model.generate_content != original_generate

    # Undo override and verify restoration
    provider.undo_override()
    assert model.generate_content == original_generate
