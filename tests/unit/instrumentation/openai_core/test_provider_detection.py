"""Tests for OpenAI-compatible provider detection.

Verifies that the provider detection utility correctly identifies
LLM providers from the OpenAI SDK client's base_url.
"""

import pytest

from agentops.instrumentation.providers.openai.provider_detection import (
    detect_provider_from_instance,
    _extract_base_url,
    _match_provider,
    _PROVIDER_HOST_MAP,
)


class MockClient:
    """Mock OpenAI client with configurable base_url."""

    def __init__(self, base_url=None):
        self.base_url = base_url


class MockResource:
    """Mock OpenAI SDK resource (e.g., Completions) with a _client attribute."""

    def __init__(self, client=None):
        self._client = client


class TestMatchProvider:
    """Tests for _match_provider function."""

    def test_minimax_io(self):
        assert _match_provider("https://api.minimax.io/v1/") == "MiniMax"

    def test_minimax_chat(self):
        assert _match_provider("https://api.minimax.chat/v1") == "MiniMax"

    def test_groq(self):
        assert _match_provider("https://api.groq.com/openai/v1") == "Groq"

    def test_together_xyz(self):
        assert _match_provider("https://api.together.xyz/v1") == "Together AI"

    def test_together_ai(self):
        assert _match_provider("https://api.together.ai/v1") == "Together AI"

    def test_fireworks(self):
        assert _match_provider("https://api.fireworks.ai/inference/v1") == "Fireworks AI"

    def test_deepseek(self):
        assert _match_provider("https://api.deepseek.com/v1") == "DeepSeek"

    def test_mistral(self):
        assert _match_provider("https://api.mistral.ai/v1") == "Mistral AI"

    def test_perplexity(self):
        assert _match_provider("https://api.perplexity.ai/") == "Perplexity AI"

    def test_xai(self):
        assert _match_provider("https://api.x.ai/v1") == "xAI"

    def test_sambanova(self):
        assert _match_provider("https://api.sambanova.ai/v1") == "SambaNova"

    def test_cerebras(self):
        assert _match_provider("https://api.cerebras.ai/v1") == "Cerebras"

    def test_openai_default(self):
        assert _match_provider("https://api.openai.com/v1") == "OpenAI"

    def test_unknown_url(self):
        assert _match_provider("https://my-custom-llm.example.com/v1") == "OpenAI"

    def test_case_insensitive(self):
        assert _match_provider("https://API.MINIMAX.IO/v1") == "MiniMax"

    def test_empty_url(self):
        assert _match_provider("") == "OpenAI"


class TestExtractBaseUrl:
    """Tests for _extract_base_url function."""

    def test_with_string_base_url(self):
        client = MockClient(base_url="https://api.minimax.io/v1/")
        resource = MockResource(client=client)
        assert _extract_base_url(resource) == "https://api.minimax.io/v1/"

    def test_with_url_object(self):
        """Test with URL-like object that has __str__."""

        class URLObject:
            def __str__(self):
                return "https://api.minimax.io/v1/"

        client = MockClient(base_url=URLObject())
        resource = MockResource(client=client)
        assert _extract_base_url(resource) == "https://api.minimax.io/v1/"

    def test_no_client(self):
        resource = MockResource(client=None)
        assert _extract_base_url(resource) is None

    def test_no_base_url(self):
        client = MockClient(base_url=None)
        resource = MockResource(client=client)
        assert _extract_base_url(resource) is None

    def test_no_client_attribute(self):
        """Test with an object that has no _client attribute."""

        class NoClient:
            pass

        assert _extract_base_url(NoClient()) is None


class TestDetectProviderFromInstance:
    """Tests for detect_provider_from_instance function."""

    def test_minimax_provider(self):
        client = MockClient(base_url="https://api.minimax.io/v1/")
        resource = MockResource(client=client)
        assert detect_provider_from_instance(resource) == "MiniMax"

    def test_groq_provider(self):
        client = MockClient(base_url="https://api.groq.com/openai/v1")
        resource = MockResource(client=client)
        assert detect_provider_from_instance(resource) == "Groq"

    def test_openai_provider(self):
        client = MockClient(base_url="https://api.openai.com/v1")
        resource = MockResource(client=client)
        assert detect_provider_from_instance(resource) == "OpenAI"

    def test_none_instance(self):
        assert detect_provider_from_instance(None) == "OpenAI"

    def test_no_client_attribute(self):
        assert detect_provider_from_instance(object()) == "OpenAI"

    def test_no_base_url(self):
        client = MockClient(base_url=None)
        resource = MockResource(client=client)
        assert detect_provider_from_instance(resource) == "OpenAI"

    def test_deepseek_provider(self):
        client = MockClient(base_url="https://api.deepseek.com/v1")
        resource = MockResource(client=client)
        assert detect_provider_from_instance(resource) == "DeepSeek"

    def test_all_registered_providers(self):
        """Verify all providers in the host map are detectable."""
        for host, expected_name in _PROVIDER_HOST_MAP.items():
            client = MockClient(base_url=f"https://{host}/v1")
            resource = MockResource(client=client)
            result = detect_provider_from_instance(resource)
            assert result == expected_name, (
                f"Expected '{expected_name}' for host '{host}', got '{result}'"
            )
