import asyncio
import os
import agentops
from dotenv import load_dotenv
import litellm

load_dotenv()

def test_litellm_integration():
    """Integration test demonstrating all four LiteLLM call patterns:
    1. Sync (non-streaming)
    2. Sync (streaming)
    3. Async (non-streaming)
    4. Async (streaming)

    Verifies that AgentOps correctly tracks all LLM calls via analytics.
    """
    # Initialize AgentOps without auto-starting session
    agentops.init(auto_start_session=False)
    session = agentops.start_session()
    
    # Initialize LiteLLM provider
    from agentops.llms.providers.litellm import LiteLLMProvider
    provider = LiteLLMProvider(None)  # LiteLLM doesn't need a client
    provider.override()
    
    # Pass session to provider
    provider.client = session

    def sync_no_stream():
        litellm.completion(
            model="gpt-3.5-turbo",
            messages=[{"content": "Hello from sync no stream", "role": "user"}],
            session=session
        )

    def sync_stream():
        stream_response = litellm.completion(
            model="gpt-3.5-turbo",
            messages=[{"content": "Hello from sync streaming", "role": "user"}],
            stream=True,
            session=session
        )
        for _ in stream_response:
            pass

    async def async_no_stream():
        await litellm.acompletion(
            model="gpt-3.5-turbo",
            messages=[{"content": "Hello from async no stream", "role": "user"}],
            session=session
        )

    async def async_stream():
        async_stream_response = await litellm.acompletion(
            model="gpt-3.5-turbo",
            messages=[{"content": "Hello from async streaming", "role": "user"}],
            stream=True,
            session=session
        )
        # Handle streaming response
        if isinstance(async_stream_response, str):
            _ = async_stream_response
        else:
            async for chunk in async_stream_response:
                _ = chunk.choices[0].delta.content if hasattr(chunk.choices[0].delta, "content") else ""

    async def run_async_tests():
        await async_no_stream()
        await async_stream()

    # Call each function with proper error handling
    try:
        sync_no_stream()
        sync_stream()
        asyncio.run(run_async_tests())
    except Exception as e:
        print(f"Error during LiteLLM test: {str(e)}")
        raise

    session.end_session("Success")
    analytics = session.get_analytics()
    print(analytics)
    # Verify that all LLM calls were tracked
    assert analytics["LLM calls"] >= 4, f"Expected at least 4 LLM calls, but got {analytics['LLM calls']}"

if __name__ == "__main__":
    test_litellm_integration()
