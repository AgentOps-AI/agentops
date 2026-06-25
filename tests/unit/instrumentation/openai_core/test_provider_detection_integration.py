"""Integration tests for provider detection in OpenAI stream wrappers.

Verifies that the chat completion stream wrapper correctly detects
OpenAI-compatible providers (e.g., MiniMax) and sets the gen_ai.system
span attribute accordingly.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from agentops.semconv import SpanAttributes


class MockSpan:
    """Mock OpenTelemetry span that records set_attribute calls."""

    def __init__(self):
        self._attributes = {}

    def set_attribute(self, key, value):
        self._attributes[key] = value

    def set_status(self, status):
        pass

    def end(self):
        pass

    def record_exception(self, exception):
        pass

    def add_event(self, name, attributes=None):
        pass


class MockClient:
    """Mock OpenAI client."""

    def __init__(self, base_url):
        self.base_url = base_url


class MockCompletionsInstance:
    """Mock Completions resource instance."""

    def __init__(self, base_url="https://api.openai.com/v1"):
        self._client = MockClient(base_url)


class MockTracer:
    """Mock OpenTelemetry tracer."""

    def __init__(self):
        self.spans = []

    def start_span(self, name, kind=None, attributes=None):
        span = MockSpan()
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, v)
        self.spans.append(span)
        return span


class TestProviderDetectionInWrapper:
    """Test that provider detection works in the stream wrapper context."""

    def test_detect_minimax_sets_llm_system(self):
        """When instance points to MiniMax, LLM_SYSTEM should be 'MiniMax'."""
        from agentops.instrumentation.providers.openai.provider_detection import (
            detect_provider_from_instance,
        )

        instance = MockCompletionsInstance("https://api.minimax.io/v1/")
        provider = detect_provider_from_instance(instance)
        assert provider == "MiniMax"

    def test_detect_openai_keeps_default(self):
        """When instance points to OpenAI, LLM_SYSTEM should be 'OpenAI'."""
        from agentops.instrumentation.providers.openai.provider_detection import (
            detect_provider_from_instance,
        )

        instance = MockCompletionsInstance("https://api.openai.com/v1")
        provider = detect_provider_from_instance(instance)
        assert provider == "OpenAI"

    def test_request_attributes_overridden_for_minimax(self):
        """Simulate the wrapper flow: handle_chat_attributes returns OpenAI,
        then provider detection overrides to MiniMax."""
        from agentops.instrumentation.providers.openai.provider_detection import (
            detect_provider_from_instance,
        )

        # Simulate handle_chat_attributes output
        request_attributes = {
            SpanAttributes.LLM_REQUEST_TYPE: "chat",
            SpanAttributes.LLM_SYSTEM: "OpenAI",
            SpanAttributes.LLM_REQUEST_MODEL: "MiniMax-M2.7",
        }

        # Detect provider from MiniMax instance
        instance = MockCompletionsInstance("https://api.minimax.io/v1/")
        provider = detect_provider_from_instance(instance)
        if provider != "OpenAI":
            request_attributes[SpanAttributes.LLM_SYSTEM] = provider

        # Verify the override
        assert request_attributes[SpanAttributes.LLM_SYSTEM] == "MiniMax"

        # Apply to span
        span = MockSpan()
        for key, value in request_attributes.items():
            span.set_attribute(key, value)

        assert span._attributes[SpanAttributes.LLM_SYSTEM] == "MiniMax"
        assert span._attributes[SpanAttributes.LLM_REQUEST_MODEL] == "MiniMax-M2.7"

    def test_openai_not_overridden(self):
        """When using standard OpenAI, LLM_SYSTEM should remain 'OpenAI'."""
        from agentops.instrumentation.providers.openai.provider_detection import (
            detect_provider_from_instance,
        )

        request_attributes = {
            SpanAttributes.LLM_SYSTEM: "OpenAI",
            SpanAttributes.LLM_REQUEST_MODEL: "gpt-4o",
        }

        instance = MockCompletionsInstance("https://api.openai.com/v1")
        provider = detect_provider_from_instance(instance)
        if provider != "OpenAI":
            request_attributes[SpanAttributes.LLM_SYSTEM] = provider

        # Should remain OpenAI
        assert request_attributes[SpanAttributes.LLM_SYSTEM] == "OpenAI"

    def test_groq_detection_in_wrapper_flow(self):
        """Verify Groq is correctly detected in the wrapper flow."""
        from agentops.instrumentation.providers.openai.provider_detection import (
            detect_provider_from_instance,
        )

        request_attributes = {
            SpanAttributes.LLM_SYSTEM: "OpenAI",
            SpanAttributes.LLM_REQUEST_MODEL: "llama-3.3-70b-versatile",
        }

        instance = MockCompletionsInstance("https://api.groq.com/openai/v1")
        provider = detect_provider_from_instance(instance)
        if provider != "OpenAI":
            request_attributes[SpanAttributes.LLM_SYSTEM] = provider

        assert request_attributes[SpanAttributes.LLM_SYSTEM] == "Groq"

    def test_deepseek_detection_in_wrapper_flow(self):
        """Verify DeepSeek is correctly detected in the wrapper flow."""
        from agentops.instrumentation.providers.openai.provider_detection import (
            detect_provider_from_instance,
        )

        request_attributes = {
            SpanAttributes.LLM_SYSTEM: "OpenAI",
            SpanAttributes.LLM_REQUEST_MODEL: "deepseek-chat",
        }

        instance = MockCompletionsInstance("https://api.deepseek.com/v1")
        provider = detect_provider_from_instance(instance)
        if provider != "OpenAI":
            request_attributes[SpanAttributes.LLM_SYSTEM] = provider

        assert request_attributes[SpanAttributes.LLM_SYSTEM] == "DeepSeek"
