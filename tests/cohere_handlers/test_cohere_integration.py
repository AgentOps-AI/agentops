import os
import pytest
import agentops
import asyncio
import cohere
from cohere.types.chat_text_generation_event import ChatTextGenerationEvent
from cohere.types.chat_stream_start_event import ChatStreamStartEvent
from cohere.types.chat_stream_end_event import ChatStreamEndEvent


@pytest.mark.integration
def test_cohere_integration():
    """Integration test demonstrating all four Cohere call patterns:
    1. Sync (non-streaming)
    2. Sync (streaming)
    3. Async (non-streaming)
    4. Async (streaming)

    Verifies that AgentOps correctly tracks all LLM calls via analytics.
    """
    print("AGENTOPS_API_KEY present:", bool(os.getenv("AGENTOPS_API_KEY")))
    print("COHERE_API_KEY present:", bool(os.getenv("COHERE_API_KEY")))

    # Initialize AgentOps without auto-starting session
    agentops.init(auto_start_session=False)
    session = agentops.start_session()

    def sync_no_stream():
        client = cohere.Client(api_key=os.getenv("COHERE_API_KEY"))
        client.chat(
            message="Hello from sync no stream",
            model="command",
            max_tokens=100,
        )

    def sync_stream():
        client = cohere.Client(api_key=os.getenv("COHERE_API_KEY"))
        stream_result = client.chat(
            message="Hello from sync streaming",
            model="command",
            max_tokens=100,
            stream=True,
        )
        for chunk in stream_result:
            if isinstance(chunk, ChatTextGenerationEvent):
                continue
            elif isinstance(chunk, ChatStreamStartEvent):
                continue
            elif isinstance(chunk, ChatStreamEndEvent):
                break

    async def async_no_stream():
        client = cohere.AsyncClient(api_key=os.getenv("COHERE_API_KEY"))
        await client.chat(
            message="Hello from async no stream",
            model="command",
            max_tokens=100,
        )

    async def async_stream():
        client = cohere.AsyncClient(api_key=os.getenv("COHERE_API_KEY"))
        async_stream_result = await client.chat(
            message="Hello from async streaming",
            model="command",
            max_tokens=100,
            stream=True,
        )
        async for chunk in async_stream_result:
            if isinstance(chunk, ChatTextGenerationEvent):
                continue
            elif isinstance(chunk, ChatStreamStartEvent):
                continue
            elif isinstance(chunk, ChatStreamEndEvent):
                break

    # Call each function
    sync_no_stream()
    sync_stream()
    asyncio.run(async_no_stream())
    asyncio.run(async_stream())
    session.end_session("Success")
    analytics = session.get_analytics()
    print(analytics)
    # Verify that all LLM calls were tracked
    assert analytics["LLM calls"] >= 4, f"Expected at least 4 LLM calls, but got {analytics['LLM calls']}"
