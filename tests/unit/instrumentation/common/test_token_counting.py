from agentops.instrumentation.common.token_counting import TokenUsage
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
