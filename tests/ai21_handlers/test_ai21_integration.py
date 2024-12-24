import os
import pytest
import agentops
import asyncio
import ai21  # Import module to trigger provider initialization
from ai21 import AI21Client, AsyncAI21Client
from ai21.models.chat import ChatMessage


@pytest.mark.integration
def test_ai21_integration():
    """Integration test demonstrating all four AI21 call patterns:
    1. Sync (non-streaming)
    2. Sync (streaming)
    3. Async (non-streaming)
    4. Async (streaming)

    Verifies that AgentOps correctly tracks all LLM calls via analytics.
    """
    print("AGENTOPS_API_KEY present:", bool(os.getenv("AGENTOPS_API_KEY")))
    print("AI21_API_KEY present:", bool(os.getenv("AI21_API_KEY")))

    # Initialize AgentOps without auto-starting session
    agentops.init(auto_start_session=False)
    session = agentops.start_session()

    def sync_no_stream():
        client = AI21Client(api_key=os.getenv("AI21_API_KEY"))
        messages = [ChatMessage(content="Hello from sync no stream", role="user")]
        client.chat.completions.create(
            messages=messages,
            model="jamba-1.5-large",
            max_tokens=20,
        )

    def sync_stream():
        client = AI21Client(api_key=os.getenv("AI21_API_KEY"))
        messages = [ChatMessage(content="Hello from sync streaming", role="user")]
        response = client.chat.completions.create(
            messages=messages,
            model="jamba-1.5-large",
            max_tokens=20,
            stream=True,
        )
        for chunk in response:
            if hasattr(chunk, "choices") and chunk.choices[0].delta.content:
                pass

    async def async_no_stream():
        client = AsyncAI21Client(api_key=os.getenv("AI21_API_KEY"))
        messages = [ChatMessage(content="Hello from async no stream", role="user")]
        await client.chat.completions.create(
            messages=messages,
            model="jamba-1.5-large",
            max_tokens=20,
        )

    async def async_stream():
        client = AsyncAI21Client(api_key=os.getenv("AI21_API_KEY"))
        messages = [ChatMessage(content="Hello from async streaming", role="user")]
        response = await client.chat.completions.create(
            messages=messages,
            model="jamba-1.5-large",
            max_tokens=20,
            stream=True,
        )
        async for chunk in response:
            if hasattr(chunk, "choices") and chunk.choices[0].delta.content:
                pass

    # Call each function
    sync_no_stream()
    sync_stream()
    asyncio.run(async_no_stream())
    asyncio.run(async_stream())
    session.end_session("Success")
    analytics = session.get_analytics()
    print("Final analytics:", analytics)
    # Verify that all LLM calls were tracked
    assert analytics["LLM calls"] >= 4, f"Expected at least 4 LLM calls, but got {analytics['LLM calls']}"
