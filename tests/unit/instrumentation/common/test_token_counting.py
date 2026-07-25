from types import SimpleNamespace

from agentops.instrumentation.common.token_counting import TokenUsage, TokenUsageExtractor
from agentops.semconv import SpanAttributes


class TestTokenUsageToAttributes:
    def test_skips_zero_values(self):
        usage = TokenUsage(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cached_prompt_tokens=0,
            cached_read_tokens=0,
            reasoning_tokens=0,
        )

        attrs = usage.to_attributes()
        assert attrs == {}

    def test_includes_positive_values_only(self):
        usage = TokenUsage(prompt_tokens=5, completion_tokens=0, total_tokens=5)
        attrs = usage.to_attributes()
        assert SpanAttributes.LLM_USAGE_PROMPT_TOKENS in attrs
        assert attrs[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 5
        assert SpanAttributes.LLM_USAGE_COMPLETION_TOKENS not in attrs
        assert SpanAttributes.LLM_USAGE_TOTAL_TOKENS in attrs
        assert attrs[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 5


class TestTokenUsageExtractor:
    def test_extracts_object_usage(self):
        response = SimpleNamespace(
            usage=SimpleNamespace(
                prompt_tokens=6,
                completion_tokens=3,
                total_tokens=9,
            )
        )

        usage = TokenUsageExtractor.extract_from_response(response)

        assert usage == TokenUsage(prompt_tokens=6, completion_tokens=3, total_tokens=9)

    def test_extracts_mapping_usage(self):
        response = SimpleNamespace(
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "cached_prompt_tokens": 3,
                "cache_read_input_tokens": 2,
                "reasoning_tokens": 1,
            }
        )

        usage = TokenUsageExtractor.extract_from_response(response)

        assert usage == TokenUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cached_prompt_tokens=3,
            cached_read_tokens=2,
            reasoning_tokens=1,
        )

    def test_extracts_mapping_usage_metadata(self):
        response = SimpleNamespace(
            usage_metadata={
                "prompt_tokens": 8,
                "completion_tokens": 4,
                "total_tokens": 12,
            }
        )

        usage = TokenUsageExtractor.extract_from_response(response)

        assert usage == TokenUsage(prompt_tokens=8, completion_tokens=4, total_tokens=12)
