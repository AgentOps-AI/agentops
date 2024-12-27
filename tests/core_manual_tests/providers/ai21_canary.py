import asyncio
import os
import agentops
from dotenv import load_dotenv
import ai21
from ai21.models.chat import ChatMessage
from ai21.clients.studio.resources.chat import ChatCompletions, AsyncChatCompletions

load_dotenv()

# Check for required API key
if not os.getenv("AI21_API_KEY"):
    raise ValueError("AI21_API_KEY environment variable is required")

def test_ai21_integration():
    """Integration test demonstrating all four AI21 call patterns:
    1. Sync (non-streaming)
    2. Sync (streaming)
    3. Async (non-streaming)
    4. Async (streaming)

    Verifies that AgentOps correctly tracks all LLM calls via analytics.
    """
    # Initialize AgentOps without auto-starting session
    agentops.init(auto_start_session=False)
    session = agentops.start_session()

    api_key = os.getenv("AI21_API_KEY")
    # Initialize provider
    from agentops.llms.providers.ai21 import AI21Provider
    provider = AI21Provider(None)  # AI21 doesn't need a client instance
    provider.override()
    
    # Pass session to provider
    provider.client = session
    ai21_client = ai21.AI21Client(api_key=api_key)
    async_ai21_client = ai21.AsyncAI21Client(api_key=api_key)
    chat_client = ChatCompletions(client=ai21_client)
    async_chat_client = AsyncChatCompletions(client=async_ai21_client)

    # Create message objects
    base_messages = [
        ChatMessage(role="system", content="You are a helpful AI assistant"),
        ChatMessage(role="user", content="Hello from the test suite")
    ]
    sync_messages = base_messages.copy()
    sync_stream_messages = base_messages.copy()
    async_messages = base_messages.copy()
    async_stream_messages = base_messages.copy()

    def sync_no_stream():
        chat_client.create(
            model="jamba-instruct",
            system="You are a helpful AI assistant",
            messages=sync_messages,
            maxTokens=10
        )

    def sync_stream():
        stream_response = chat_client.create(
            model="jamba-instruct",
            system="You are a helpful AI assistant",
            messages=sync_stream_messages,
            maxTokens=10,
            stream=True
        )
        for chunk in stream_response:
            _ = chunk.choices[0].delta.content if hasattr(chunk.choices[0].delta, "content") else ""

    async def async_no_stream():
        await async_chat_client.create(
            model="jamba-instruct",
            system="You are a helpful AI assistant",
            messages=async_messages,
            maxTokens=10
        )

    async def async_stream():
        async_stream_response = await async_chat_client.create(
            model="jamba-instruct",
            system="You are a helpful AI assistant",
            messages=async_stream_messages,
            maxTokens=10,
            stream=True
        )
        async for chunk in async_stream_response:
            _ = chunk.choices[0].delta.content if hasattr(chunk.choices[0].delta, 'content') else ''

    async def run_async_tests():
        await async_no_stream()
        await async_stream()

    # Call each function with proper error handling
    try:
        sync_no_stream()
        sync_stream()
        asyncio.run(run_async_tests())
    except Exception as e:
        print(f"Error during AI21 test: {str(e)}")
        raise
    finally:
        session.end_session("Success")
        analytics = session.get_analytics()
        print(f"Analytics: {analytics}")
        assert analytics["LLM calls"] >= 4, f"Expected at least 4 LLM calls, but got {analytics['LLM calls']}"

    # Analytics verification is handled in the finally block

if __name__ == "__main__":
    test_ai21_integration()
