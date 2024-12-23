import pytest
import agentops
import asyncio
import os
from unittest.mock import patch, MagicMock
from agentops import record_action
from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion import Choice, ChatCompletionMessage
from dotenv import load_dotenv

load_dotenv()


def mock_completion():
    return ChatCompletion(
        id="mock-id",
        model="gpt-3.5-turbo",
        object="chat.completion",
        choices=[
            Choice(
                finish_reason="stop", index=0, message=ChatCompletionMessage(content="Mock response", role="assistant")
            )
        ],
        created=1234567890,
    )


def mock_stream():
    return [
        ChatCompletionChunk(
            id="mock-id",
            model="gpt-3.5-turbo",
            object="chat.completion.chunk",
            choices=[
                Choice(delta=ChatCompletionMessage(content="Mock chunk", role="assistant"), finish_reason=None, index=0)
            ],
            created=1234567890,
        )
    ]


@pytest.mark.integration
def test_openai_integration():
    """Integration test demonstrating all four OpenAI call patterns:
    1. Sync (non-streaming)
    2. Sync (streaming)
    3. Async (non-streaming)
    4. Async (streaming)

    Verifies that AgentOps correctly tracks all LLM calls via analytics.
    """
    # Check if we have necessary API keys
    has_keys = bool(os.getenv("OPENAI_API_KEY")) and bool(os.getenv("AGENTOPS_API_KEY"))

    # Initialize AgentOps without auto-starting session
    agentops.init(auto_start_session=False)
    session = agentops.start_session()

    @record_action("openai-integration-sync-no-stream")
    def sync_no_stream():
        if has_keys:
            client = OpenAI()
            client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello from sync no stream"}],
            )
        else:
            with patch("openai.resources.chat.completions.Completions.create", return_value=mock_completion()):
                client = OpenAI(api_key="mock-key")
                client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hello from sync no stream"}],
                )

    @record_action("openai-integration-sync-stream")
    def sync_stream():
        if has_keys:
            client = OpenAI()
            stream_result = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello from sync streaming"}],
                stream=True,
            )
            for _ in stream_result:
                pass
        else:
            with patch("openai.resources.chat.completions.Completions.create", return_value=mock_stream()):
                client = OpenAI(api_key="mock-key")
                stream_result = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hello from sync streaming"}],
                    stream=True,
                )
                for _ in stream_result:
                    pass

    @record_action("openai-integration-async-no-stream")
    async def async_no_stream():
        if has_keys:
            client = AsyncOpenAI()
            await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello from async no stream"}],
            )
        else:
            with patch("openai.resources.chat.completions.AsyncCompletions.create", return_value=mock_completion()):
                client = AsyncOpenAI(api_key="mock-key")
                await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hello from async no stream"}],
                )

    @record_action("openai-integration-async-stream")
    async def async_stream():
        if has_keys:
            client = AsyncOpenAI()
            async_stream_result = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello from async streaming"}],
                stream=True,
            )
            async for _ in async_stream_result:
                pass
        else:
            with patch("openai.resources.chat.completions.AsyncCompletions.create", return_value=mock_stream()):
                client = AsyncOpenAI(api_key="mock-key")
                async_stream_result = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hello from async streaming"}],
                    stream=True,
                )
                async for _ in async_stream_result:
                    pass

    # Call each function
    sync_no_stream()
    sync_stream()
    asyncio.run(async_no_stream())
    asyncio.run(async_stream())

    session.end_session("Success")
    analytics = session.get_analytics()

    # Verify that all LLM calls were tracked
    assert analytics["LLM calls"] >= 4, f"Expected at least 4 LLM calls, but got {analytics['LLM calls']}"
