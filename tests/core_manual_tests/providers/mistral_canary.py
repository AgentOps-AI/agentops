import asyncio
import os
import agentops
from dotenv import load_dotenv
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

load_dotenv()

# Check for required API key
if not os.getenv("MISTRAL_API_KEY"):
    raise ValueError("MISTRAL_API_KEY environment variable is required")

def test_mistral_integration():
    """Integration test demonstrating all four Mistral call patterns:
    1. Sync (non-streaming)
    2. Sync (streaming)
    3. Async (non-streaming)
    4. Async (streaming)

    Verifies that AgentOps correctly tracks all LLM calls via analytics.
    """
    # Initialize AgentOps without auto-starting session
    agentops.init(auto_start_session=False)
    session = agentops.start_session()

    # Initialize client and provider
    client = MistralClient(api_key=os.getenv("MISTRAL_API_KEY"))
    from agentops.llms.providers.mistral import MistralProvider
    provider = MistralProvider(client)
    provider.override()
    
    # Pass session to provider
    provider.client = session

    def sync_no_stream():
        client.chat(
            model="mistral-tiny",
            messages=[ChatMessage(role="user", content="Hello from sync no stream")]
        )

    async def sync_stream():
        stream_response = await client.chat_stream(
            model="mistral-tiny",
            messages=[ChatMessage(role="user", content="Hello from sync streaming")]
        )
        async for chunk in stream_response:
            _ = chunk.delta.content if hasattr(chunk.delta, "content") else ""

    async def async_no_stream():
        # Mistral doesn't have async methods, use sync
        client.chat(
            model="mistral-tiny",
            messages=[ChatMessage(role="user", content="Hello from async no stream")]
        )

    async def async_stream():
        stream_response = await client.chat_stream(
            model="mistral-tiny",
            messages=[ChatMessage(role="user", content="Hello from async streaming")]
        )
        async for chunk in stream_response:
            _ = chunk.delta.content if hasattr(chunk.delta, 'content') else ''

    async def run_async_tests():
        await async_no_stream()
        await async_stream()

    # Call each function with proper error handling
    try:
        sync_no_stream()
        asyncio.run(sync_stream())
        asyncio.run(run_async_tests())
    except Exception as e:
        print(f"Error during Mistral test: {str(e)}")
        raise

    session.end_session("Success")
    analytics = session.get_analytics()
    print(analytics)
    # Verify that all LLM calls were tracked
    assert analytics["LLM calls"] >= 4, f"Expected at least 4 LLM calls, but got {analytics['LLM calls']}"

if __name__ == "__main__":
    test_mistral_integration()
