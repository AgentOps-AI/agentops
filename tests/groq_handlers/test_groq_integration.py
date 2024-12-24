import os
import pytest
import agentops
import asyncio
import groq  # Import module to trigger provider initialization
from groq import Groq
from groq.resources.chat import AsyncCompletions

@pytest.mark.integration
def test_groq_integration():
    """Integration test demonstrating all four Groq call patterns:
    1. Sync (non-streaming)
    2. Sync (streaming)
    3. Async (non-streaming)
    4. Async (streaming)

    Verifies that AgentOps correctly tracks all LLM calls via analytics.
    """
    print("AGENTOPS_API_KEY present:", bool(os.getenv("AGENTOPS_API_KEY")))
    print("GROQ_API_KEY present:", bool(os.getenv("GROQ_API_KEY")))

    agentops.init(auto_start_session=False, instrument_llm_calls=True)
    session = agentops.start_session()
    print("Session created:", bool(session))
    print("Session ID:", session.session_id if session else None)

    def sync_no_stream():
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        client.chat.completions.create(
            messages=[{"role": "user", "content": "Hello from sync no stream"}],
            model="mixtral-8x7b-32768",
        )

    def sync_stream():
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        stream_result = client.chat.completions.create(
            messages=[{"role": "user", "content": "Hello from sync streaming"}],
            model="mixtral-8x7b-32768",
            stream=True,
        )
        for _ in stream_result:
            pass

    async def async_no_stream():
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        result = client.chat.completions.create(
            messages=[{"role": "user", "content": "Hello from async no stream"}],
            model="mixtral-8x7b-32768",
        )
        return result

    async def async_stream():
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        async_stream_result = client.chat.completions.create(
            messages=[{"role": "user", "content": "Hello from async streaming"}],
            model="mixtral-8x7b-32768",
            stream=True,
        )
        for _ in async_stream_result:
            pass

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
