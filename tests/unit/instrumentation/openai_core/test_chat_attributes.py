from openai.types.chat import ChatCompletion

from agentops.instrumentation.providers.openai.wrappers.chat import handle_chat_attributes
from agentops.semconv import SpanAttributes


def _chat_completion(usage):
    return ChatCompletion.model_validate(
        {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 0,
            "model": "o3-mini",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "hi"}}],
            "usage": usage,
        }
    )


class TestChatAttributes:
    def test_reasoning_tokens_from_completion_tokens_details(self):
        response = _chat_completion(
            {
                "prompt_tokens": 10,
                "completion_tokens": 200,
                "total_tokens": 210,
                "completion_tokens_details": {"reasoning_tokens": 192},
            }
        )

        attributes = handle_chat_attributes(kwargs={"model": "o3-mini"}, return_value=response)

        assert attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 200
        assert attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] == 192

    def test_no_reasoning_tokens_without_completion_tokens_details(self):
        response = _chat_completion({"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})

        attributes = handle_chat_attributes(kwargs={"model": "gpt-4o"}, return_value=response)

        assert SpanAttributes.LLM_USAGE_REASONING_TOKENS not in attributes
