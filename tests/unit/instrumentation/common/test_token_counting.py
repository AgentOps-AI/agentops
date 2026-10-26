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
    def test_extract_from_object_usage(self):
        usage_obj = SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            cached_prompt_tokens=2,
            cache_read_input_tokens=3,
            reasoning_tokens=5,
        )
        response = SimpleNamespace(usage=usage_obj)
        usage = TokenUsageExtractor.extract_from_response(response)

        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 20
        assert usage.total_tokens == 30
        assert usage.cached_prompt_tokens == 2
        assert usage.cached_read_tokens == 3
        assert usage.reasoning_tokens == 5

    def test_extract_from_mapping_usage_metadata(self):
        response = SimpleNamespace(
            usage_metadata={
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "cached_prompt_tokens": 4,
                "cache_read_input_tokens": 6,
                "reasoning_tokens": 2,
            }
        )
        usage = TokenUsageExtractor.extract_from_response(response)

        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 5
        assert usage.total_tokens == 15
        assert usage.cached_prompt_tokens == 4
        assert usage.cached_read_tokens == 6
        assert usage.reasoning_tokens == 2

    def test_extract_from_dict_response(self):
        response = {
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 8,
                "total_tokens": 20,
            }
        }
        usage = TokenUsageExtractor.extract_from_response(response)
        assert usage.prompt_tokens == 12
        assert usage.completion_tokens == 8
        assert usage.total_tokens == 20

    def test_extract_otel_input_output_tokens(self):
        response = SimpleNamespace(
            usage_metadata={
                "input_tokens": 42,
                "output_tokens": 18,
            }
        )
        usage = TokenUsageExtractor.extract_from_response(response)
        assert usage.prompt_tokens == 42
        assert usage.completion_tokens == 18
        assert usage.total_tokens == 60

    def test_extract_from_crewai_dict(self):
        response = SimpleNamespace(
            token_usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
            }
        )
        usage = TokenUsageExtractor.extract_from_response(response)
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_extract_from_crewai_string(self):
        response = SimpleNamespace(
            token_usage="prompt_tokens=100 completion_tokens=50"
        )
        usage = TokenUsageExtractor.extract_from_response(response)
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_extract_none_response(self):
        usage = TokenUsageExtractor.extract_from_response(None)
        assert usage.prompt_tokens is None
        assert usage.completion_tokens is None
        assert usage.total_tokens is None
