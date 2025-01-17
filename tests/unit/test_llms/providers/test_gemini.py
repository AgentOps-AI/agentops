import google.generativeai as genai
import agentops
from agentops.llms.providers.gemini import GeminiProvider, _ORIGINAL_METHODS
from agentops.event import LLMEvent

# Configure the API key from environment variable
import os
import pytest


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


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Skip all tests if GEMINI_API_KEY is not available
if not GEMINI_API_KEY:
    pytest.skip("GEMINI_API_KEY environment variable is required for Gemini tests", allow_module_level=True)

genai.configure(api_key=GEMINI_API_KEY)


def test_gemini_provider():
    """Test GeminiProvider initialization and override."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)
    assert provider.client == model
    assert provider.provider_name == "Gemini"
    assert "generate_content" not in _ORIGINAL_METHODS


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
    # Test initialization with None client
    provider = GeminiProvider(None)
    assert provider.client is None

    # Test initialization with invalid client
    class InvalidClient:
        pass

    with pytest.raises(ValueError, match="Client must have generate_content method"):
        GeminiProvider(InvalidClient())

    # Test override with None client
    provider.override()  # Should log warning and return
    assert "generate_content" not in _ORIGINAL_METHODS

    # Test override with uninitialized generate_content
    provider.client = InvalidClient()
    provider.override()  # Should log warning about missing generate_content
    assert "generate_content" not in _ORIGINAL_METHODS

    # Test patched function with missing original method
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)
    provider.override()

    # Should log error and return None when original method is missing
    if "generate_content" in _ORIGINAL_METHODS:
        del _ORIGINAL_METHODS["generate_content"]
    result = model.generate_content("test prompt")
    assert result is None

    # Test undo_override with None client
    provider.client = None
    provider.undo_override()  # Should handle None client gracefully

    # Test undo_override with missing original method
    provider.client = model
    provider.undo_override()  # Should handle missing original method gracefully

    # Test automatic provider detection
    agentops.init()
    # Test that the provider is properly cleaned up
    original_method = model.generate_content
    response = model.generate_content("test cleanup")
    assert response is not None  # Provider should be working

    agentops.stop_instrumenting()
    assert model.generate_content == original_method  # Original method should be restored


def test_gemini_handle_response():
    """Test handle_response method with various scenarios."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)
    ao_client = agentops.init()

    # Test handling response with usage metadata
    class MockResponse:
        def __init__(self, text, usage_metadata=None, model=None):
            self.text = text
            self.usage_metadata = usage_metadata
            self.model = model

    # Test successful response with usage metadata
    response = MockResponse(
        "Test response",
        usage_metadata=type("UsageMetadata", (), {"prompt_token_count": 10, "candidates_token_count": 20}),
        model="gemini-1.5-flash",
    )

    result = provider.handle_response(response, {"contents": "Test prompt"}, "2024-01-17T00:00:00Z", session=ao_client)
    assert result == response

    # Test response without usage metadata
    response_no_usage = MockResponse("Test response without usage")
    result = provider.handle_response(
        response_no_usage, {"contents": "Test prompt"}, "2024-01-17T00:00:00Z", session=ao_client
    )
    assert result == response_no_usage

    # Test response with invalid usage metadata
    response_invalid = MockResponse(
        "Test response", usage_metadata=type("InvalidUsageMetadata", (), {"invalid_field": "value"})
    )
    result = provider.handle_response(
        response_invalid, {"contents": "Test prompt"}, "2024-01-17T00:00:00Z", session=ao_client
    )
    assert result == response_invalid

    # Test error handling with malformed response
    class MalformedResponse:
        def __init__(self):
            pass

        @property
        def text(self):
            raise AttributeError("No text attribute")

    malformed_response = MalformedResponse()
    result = provider.handle_response(
        malformed_response, {"contents": "Test prompt"}, "2024-01-17T00:00:00Z", session=ao_client
    )
    assert result == malformed_response


def test_gemini_streaming_chunks():
    """Test streaming response handling with chunks."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)
    ao_client = agentops.init()

    # Use shared MockChunk class

    # Test successful streaming with various usage metadata scenarios
    chunks = [
        MockChunk("Hello", model="gemini-1.5-flash"),
        MockChunk(
            " world",
            usage_metadata=type(
                "UsageMetadata",
                (),
                {
                    "prompt_token_count": 5,
                    "candidates_token_count": 10,
                    "total_token_count": 15,
                    "invalid_field": "test",
                },
            ),
            model="gemini-1.5-flash",
        ),
        MockChunk(
            "!",
            usage_metadata=type(
                "UsageMetadata",
                (),
                {
                    "prompt_token_count": None,  # Test None token count
                    "candidates_token_count": "invalid",  # Test invalid token count
                },
            ),
            finish_reason="stop",
            model="gemini-1.5-flash",
        ),
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

    # Test streaming with various error scenarios
    error_chunks = [
        MockChunk("Start", model="gemini-1.5-flash"),
        MockChunk(None, error=ValueError("Invalid chunk"), model="gemini-1.5-flash"),
        MockChunk(
            "Middle",
            usage_metadata=type(
                "UsageMetadata",
                (),
                {
                    "prompt_token_count": "invalid",
                    "candidates_token_count": None,
                },
            ),
            error=AttributeError("Missing text"),
            model="gemini-1.5-flash",
        ),
        MockChunk("End", finish_reason="stop", model="gemini-1.5-flash"),
    ]

    def mock_error_stream():
        for chunk in error_chunks:
            yield chunk

    result = provider.handle_response(
        mock_error_stream(), {"contents": "Test prompt", "stream": True}, "2024-01-17T00:00:00Z", session=ao_client
    )

    # Verify error handling doesn't break streaming
    accumulated = []
    for chunk in result:
        if hasattr(chunk, "text") and chunk.text:
            accumulated.append(chunk.text)
    assert "".join(accumulated) == "StartEnd"

    # Test streaming with exception in chunk processing
    class ExceptionChunk:
        @property
        def text(self):
            raise Exception("Simulated chunk processing error")

    def mock_exception_stream():
        yield ExceptionChunk()
        yield MockChunk("After Error", finish_reason="stop", model="gemini-1.5-flash")

    result = provider.handle_response(
        mock_exception_stream(), {"contents": "Test prompt", "stream": True}, "2024-01-17T00:00:00Z", session=ao_client
    )

    # Verify streaming continues after exception
    accumulated = []
    for chunk in result:
        if hasattr(chunk, "text") and chunk.text:
            accumulated.append(chunk.text)
    assert "".join(accumulated) == "After Error"


def test_handle_response_errors():
    """Test error handling in handle_response method with various error scenarios."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)
    ao_client = agentops.init()

    # Test sync response with missing attributes and session=None
    class BrokenResponse:
        def __init__(self):
            pass

        @property
        def usage_metadata(self):
            raise AttributeError("No usage metadata")

        @property
        def text(self):
            raise AttributeError("No text attribute")

        @property
        def model(self):
            raise AttributeError("No model attribute")

    # Test with session=None
    result = provider.handle_response(BrokenResponse(), {"contents": "test"}, "2024-01-17T00:00:00Z")
    assert result is not None

    # Test with session
    result = provider.handle_response(BrokenResponse(), {"contents": "test"}, "2024-01-17T00:00:00Z", session=ao_client)
    assert result is not None

    # Test sync response with invalid metadata types
    class InvalidMetadataResponse:
        def __init__(self):
            self.text = "Test response"
            self.model = "gemini-1.5-flash"
            self.usage_metadata = type(
                "InvalidMetadata",
                (),
                {
                    "prompt_token_count": "invalid",
                    "candidates_token_count": None,
                    "invalid_field": "test",
                },
            )

    result = provider.handle_response(
        InvalidMetadataResponse(), {"contents": "test"}, "2024-01-17T00:00:00Z", session=ao_client
    )
    assert result is not None

    # Test sync response with malformed response object
    class MalformedResponse:
        def __getattr__(self, name):
            raise Exception(f"Accessing {name} causes error")

    result = provider.handle_response(
        MalformedResponse(), {"contents": "test"}, "2024-01-17T00:00:00Z", session=ao_client
    )
    assert result is not None

    # Test streaming response with various error scenarios
    def error_generator():
        # Test normal chunk
        yield MockChunk("Start", model="gemini-1.5-flash")
        # Test chunk with missing text
        yield MockChunk(None, model="gemini-1.5-flash")
        # Test chunk with error on text access
        yield MockChunk(None, error=ValueError("Invalid chunk"), model="gemini-1.5-flash")
        # Test chunk with invalid metadata
        yield MockChunk(
            "Middle",
            usage_metadata=type(
                "InvalidMetadata",
                (),
                {
                    "prompt_token_count": "invalid",
                    "candidates_token_count": None,
                },
            ),
            model="gemini-1.5-flash",
        )
        # Test chunk with missing model
        yield MockChunk("More", model=None)

        # Test chunk with error on model access
        class ErrorModelChunk:
            @property
            def model(self):
                raise AttributeError("No model")

            @property
            def text(self):
                return "Error model"

        yield ErrorModelChunk()
        # Test final chunk
        yield MockChunk("End", finish_reason="stop", model="gemini-1.5-flash")

    # Test with session=None
    result = provider.handle_response(error_generator(), {"contents": "test", "stream": True}, "2024-01-17T00:00:00Z")
    accumulated = []
    for chunk in result:
        if hasattr(chunk, "text") and chunk.text:
            try:
                accumulated.append(chunk.text)
            except Exception:
                pass
    assert "Start" in "".join(accumulated)
    assert "End" in "".join(accumulated)

    # Test with session
    result = provider.handle_response(
        error_generator(), {"contents": "test", "stream": True}, "2024-01-17T00:00:00Z", session=ao_client
    )
    accumulated = []
    for chunk in result:
        if hasattr(chunk, "text") and chunk.text:
            try:
                accumulated.append(chunk.text)
            except Exception:
                pass
    assert len(accumulated) > 0

    # Test streaming with exception in generator
    def exception_generator():
        yield MockChunk("Before error")
        raise Exception("Generator error")
        yield MockChunk("After error")

    result = provider.handle_response(
        exception_generator(), {"contents": "test", "stream": True}, "2024-01-17T00:00:00Z", session=ao_client
    )
    accumulated = []
    try:
        for chunk in result:
            if hasattr(chunk, "text") and chunk.text:
                accumulated.append(chunk.text)
    except Exception as e:
        assert str(e) == "Generator error"
    assert "Before error" in "".join(accumulated)


def test_override_edge_cases():
    """Test edge cases in override method."""
    # Test override with None client
    provider = GeminiProvider(None)
    provider.override()  # Should log warning and return

    # Test override with missing generate_content
    class NoGenerateClient:
        pass

    provider = GeminiProvider(NoGenerateClient())
    provider.override()  # Should log warning and return

    # Test override with custom generate_content
    class CustomClient:
        def generate_content(self, *args, **kwargs):
            return "custom response"

    client = CustomClient()
    provider = GeminiProvider(client)
    provider.override()

    # Test with various argument combinations
    assert client.generate_content("test") is not None
    assert client.generate_content(contents="test") is not None
    assert client.generate_content("test", stream=True) is not None
    assert client.generate_content(contents="test", stream=True) is not None

    # Clean up
    provider.undo_override()


def test_undo_override():
    """Test undo_override functionality."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    provider = GeminiProvider(model)

    # Store original method
    original_generate = model.generate_content

    # Override and verify
    provider.override()
    assert model.generate_content != original_generate

    # Test with positional arguments
    response = model.generate_content("test with positional arg")
    assert response is not None

    # Test with keyword arguments
    response = model.generate_content(contents="test with kwargs")
    assert response is not None

    # Test with both positional and keyword arguments
    response = model.generate_content("test prompt", stream=False)
    assert response is not None

    # Undo override and verify restoration
    provider.undo_override()
    assert model.generate_content == original_generate

    # Test undo_override with missing original method
    if "generate_content" in _ORIGINAL_METHODS:
        del _ORIGINAL_METHODS["generate_content"]
    provider.undo_override()  # Should not raise any errors
