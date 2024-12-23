import pytest
import agentops
import asyncio
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
import os

load_dotenv()


pytestmark = [pytest.mark.vcr]


@pytest.mark.integration
def test_openai_integration():
    """Integration test demonstrating all four OpenAI call patterns:
    1. Sync (non-streaming)
    2. Sync (streaming)
    3. Async (non-streaming)
    4. Async (streaming)

    Verifies that AgentOps correctly tracks all LLM calls via analytics.
    """
    # Initialize AgentOps without auto-starting session
    agentops.init(auto_start_session=False)
    session = agentops.start_session()

    def sync_no_stream():
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello from sync no stream"}],
        )

    def sync_stream():
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        stream_result = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello from sync streaming"}],
            stream=True,
        )
        for _ in stream_result:
            pass

    async def async_no_stream():
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello from async no stream"}],
        )

    async def async_stream():
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        async_stream_result = await client.chat.completions.create(
            model="gpt-4o-mini",
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
    print(analytics)
    # Verify that all LLM calls were tracked
    assert analytics["LLM calls"] >= 4, f"Expected at least 4 LLM calls, but got {analytics['LLM calls']}"
