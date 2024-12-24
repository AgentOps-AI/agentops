import os
import pytest
import agentops
import asyncio
import litellm

@pytest.mark.integration
def test_litellm_integration():
    """Integration test demonstrating all four LiteLLM call patterns:
    1. Sync (non-streaming)
    2. Sync (streaming)
    3. Async (non-streaming)
    4. Async (streaming)

    Verifies that AgentOps correctly tracks all LLM calls via analytics.
    Uses Anthropic's Claude model as the backend provider.
    """
    print("AGENTOPS_API_KEY present:", bool(os.getenv("AGENTOPS_API_KEY")))
    print("ANTHROPIC_API_KEY present:", bool(os.getenv("ANTHROPIC_API_KEY")))  # LiteLLM uses Anthropic

    agentops.init(auto_start_session=False, instrument_llm_calls=True)
    session = agentops.start_session()
    print("Session created:", bool(session))
    print("Session ID:", session.session_id if session else None)

    def sync_no_stream():
        litellm.api_key = os.getenv("ANTHROPIC_API_KEY")
        litellm.completion(
            model="anthropic/claude-3-opus-20240229",
            messages=[{"role": "user", "content": "Hello from sync no stream"}],
        )

    def sync_stream():
        litellm.api_key = os.getenv("ANTHROPIC_API_KEY")
        stream_result = litellm.completion(
            model="anthropic/claude-3-opus-20240229",
            messages=[{"role": "user", "content": "Hello from sync streaming"}],
            stream=True,
        )
        for chunk in stream_result:
            if hasattr(chunk, "choices") and chunk.choices[0].delta.content:
                pass

    async def async_no_stream():
        litellm.api_key = os.getenv("ANTHROPIC_API_KEY")
        await litellm.acompletion(
            model="anthropic/claude-3-opus-20240229",
            messages=[{"role": "user", "content": "Hello from async no stream"}],
        )

    async def async_stream():
        litellm.api_key = os.getenv("ANTHROPIC_API_KEY")
        async_stream_result = await litellm.acompletion(
            model="anthropic/claude-3-opus-20240229",
            messages=[{"role": "user", "content": "Hello from async streaming"}],
            stream=True,
        )
        async for chunk in async_stream_result:
            if hasattr(chunk, "choices") and chunk.choices[0].delta.content:
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
