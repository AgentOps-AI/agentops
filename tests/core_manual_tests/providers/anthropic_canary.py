import asyncio
import os
import agentops
from dotenv import load_dotenv
import anthropic

load_dotenv()

def test_anthropic_integration():
    """Integration test demonstrating all four Anthropic call patterns:
    1. Sync (non-streaming)
    2. Sync (streaming)
    3. Async (non-streaming)
    4. Async (streaming)

    Verifies that AgentOps correctly tracks all LLM calls via analytics.
    """
    # Initialize AgentOps without auto-starting session
    agentops.init(auto_start_session=False)
    session = agentops.start_session()

    # Initialize clients and provider
    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    async_anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    from agentops.llms.providers.anthropic import AnthropicProvider
    provider = AnthropicProvider(anthropic_client)
    provider.override()
    
    # Pass session to provider
    provider.client = session

    def sync_no_stream():
        anthropic_client.messages.create(
            max_tokens=1024,
            model="claude-3-5-sonnet-20240620",
            messages=[
                {
                    "role": "user",
                    "content": "Hello from sync no stream",
                }
            ],
            session=session
        )

    def sync_stream():
        stream_response = anthropic_client.messages.create(
            max_tokens=1024,
            model="claude-3-5-sonnet-20240620",
            messages=[
                {
                    "role": "user",
                    "content": "Hello from sync streaming",
                }
            ],
            stream=True,
            session=session
        )
        for _ in stream_response:
            pass

    async def async_no_stream():
        await async_anthropic_client.messages.create(
            max_tokens=1024,
            model="claude-3-5-sonnet-20240620",
            messages=[
                {
                    "role": "user",
                    "content": "Hello from async no stream",
                }
            ],
            session=session
        )

    async def async_stream():
        async_stream_response = await async_anthropic_client.messages.create(
            max_tokens=1024,
            model="claude-3-5-sonnet-20240620",
            messages=[
                {
                    "role": "user",
                    "content": "Hello from async streaming",
                }
            ],
            stream=True,
            session=session
        )
        async for _ in async_stream_response:
            pass

    async def run_async_tests():
        await async_no_stream()
        await async_stream()

    # Call each function with proper error handling
    try:
        sync_no_stream()
        sync_stream()
        asyncio.run(run_async_tests())
    except Exception as e:
        print(f"Error during Anthropic test: {str(e)}")
        raise

    session.end_session("Success")
    analytics = session.get_analytics()
    print(analytics)
    # Verify that all LLM calls were tracked
    assert analytics["LLM calls"] >= 4, f"Expected at least 4 LLM calls, but got {analytics['LLM calls']}"

if __name__ == "__main__":
    test_anthropic_integration()
