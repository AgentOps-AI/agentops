import os
import pytest
import agentops
import asyncio
import mistralai  # Import module to trigger provider initialization
from mistralai import Mistral

@pytest.mark.integration
def test_mistral_integration():
    """Integration test demonstrating all four Mistral call patterns:
    1. Sync (non-streaming)
    2. Sync (streaming)
    3. Async (non-streaming)
    4. Async (streaming)

    Verifies that AgentOps correctly tracks all LLM calls via analytics.
    """
    print("AGENTOPS_API_KEY present:", bool(os.getenv("AGENTOPS_API_KEY")))
    print("MISTRAL_API_KEY present:", bool(os.getenv("MISTRAL_API_KEY")))
    
    agentops.init(auto_start_session=False, instrument_llm_calls=True)
    session = agentops.start_session()
    print("Session created:", bool(session))
    print("Session ID:", session.session_id if session else None)

    def sync_no_stream():
        client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": "Hello from sync no stream"}],
        )

    def sync_stream():
        client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        stream_result = client.chat.stream(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": "Hello from sync streaming"}],
        )
        for chunk in stream_result:
            print(chunk.data.choices[0].delta.content, end="")

    async def async_no_stream():
        client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        await client.chat.complete_async(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": "Hello from async no stream"}],
        )

    async def async_stream():
        client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        async_stream_result = await client.chat.stream_async(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": "Hello from async streaming"}],
        )
        async for chunk in async_stream_result:
            print(chunk.data.choices[0].delta.content, end="")

    try:
        # Call each function
        sync_no_stream()
        sync_stream()
        asyncio.run(async_no_stream())
        asyncio.run(async_stream())
    finally:
        session.end_session("Success")
    analytics = session.get_analytics()
    print(analytics)
    # Verify that all LLM calls were tracked
    assert analytics["LLM calls"] >= 4, f"Expected at least 4 LLM calls, but got {analytics['LLM calls']}"
