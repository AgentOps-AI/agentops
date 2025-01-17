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
