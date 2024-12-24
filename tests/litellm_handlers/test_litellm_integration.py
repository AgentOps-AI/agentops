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

    # Initialize AgentOps without auto-starting session
    agentops.init(auto_start_session=False)
    session = agentops.start_session()

    # Set API key once at the start
    litellm.api_key = os.getenv("ANTHROPIC_API_KEY")

    async def run_all_tests():
        # Sync non-streaming (using acompletion for consistency)
        await litellm.acompletion(
            model="anthropic/claude-2",
            messages=[{"role": "user", "content": "Hello from sync no stream"}],
            max_tokens=100,
        )

        # Sync streaming
        response = await litellm.acompletion(
            model="anthropic/claude-2",
            messages=[{"role": "user", "content": "Hello from sync streaming"}],
            stream=True,
            max_tokens=100,
        )
        async for chunk in response:
            if hasattr(chunk, "choices") and chunk.choices[0].delta.content:
                pass

        # Async non-streaming
        await litellm.acompletion(
            model="anthropic/claude-2",
            messages=[{"role": "user", "content": "Hello from async no stream"}],
            max_tokens=100,
        )

        # Async streaming
        async_stream_result = await litellm.acompletion(
            model="anthropic/claude-2",
            messages=[{"role": "user", "content": "Hello from async streaming"}],
            stream=True,
            max_tokens=100,
        )
        async for chunk in async_stream_result:
            if hasattr(chunk, "choices") and chunk.choices[0].delta.content:
                pass

    # Run all tests in a single event loop
    asyncio.run(run_all_tests())

    # End session and verify analytics
    session.end_session("Success")
    analytics = session.get_analytics()
    print(analytics)
    # Verify that all LLM calls were tracked
    assert analytics["LLM calls"] >= 4, f"Expected at least 4 LLM calls, but got {analytics['LLM calls']}"
