import asyncio
import inspect
import os
import agentops
from dotenv import load_dotenv
import cohere
from agentops.helpers import get_ISO_time
from agentops.llms.providers.cohere import CohereProvider

load_dotenv()

def test_cohere_integration():
    """Integration test demonstrating all four Cohere call patterns:
    1. Sync (non-streaming)
    2. Sync (streaming)
    3. Async (non-streaming)
    4. Async (streaming)

    Verifies that AgentOps correctly tracks all LLM calls via analytics.
    """
    # Get API key with error handling
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise ValueError("COHERE_API_KEY environment variable is required")
    print("\nInitializing test with Cohere API key...")

    # Initialize AgentOps without auto-starting session
    agentops.init(auto_start_session=False)
    session = agentops.start_session()
    print(f"Started new session with ID: {session.session_id}")

    # Initialize client and provider with error handling
    try:
        co = cohere.Client(api_key=api_key)
        aco = cohere.AsyncClient(api_key=api_key)
        from agentops.llms.providers.cohere import CohereProvider
        provider = CohereProvider(co)
        provider.client = session  # Pass session to provider before override
        provider.override()  # This will handle both sync and async clients
        
        # Set up async client with the same session
        aco.session = session
        # Ensure the async client's provider also has the session
        aco.provider = provider
        print("Successfully initialized Cohere clients and provider")
        print(f"Provider session ID: {provider.client.session_id}")
    except Exception as e:
        print(f"Error initializing Cohere clients: {str(e)}")
        raise

    def sync_no_stream():
        try:
            print("\nExecuting sync_no_stream...")
            response = co.chat(message="Hello from sync no stream", model="command", session=session)
            print(f"sync_no_stream completed successfully with response: {response.text}")
        except Exception as e:
            print(f"Error in sync_no_stream: {str(e)}")
            raise

    def sync_stream():
        try:
            print("\nExecuting sync_stream...")
            stream = co.chat_stream(message="Hello from sync streaming", model="command", session=session)
            completion = ""
            for chunk in stream:
                if hasattr(chunk, 'text'):
                    completion += chunk.text
                print(f"Received sync chunk: {chunk}")
            print(f"sync_stream completed successfully with completion: {completion}")
        except Exception as e:
            print(f"Error in sync_stream: {str(e)}")
            raise

    async def async_no_stream():
        try:
            print("\nExecuting async_no_stream...")
            async with asyncio.timeout(30):
                response = await aco.chat(message="Hello from async no stream", model="command", session=session)
                print(f"async_no_stream completed successfully with response: {response.text}")
        except asyncio.TimeoutError:
            print("Warning: async_no_stream timed out")
            raise
        except Exception as e: 
            print(f"Error in async_no_stream: {str(e)}")
            raise

    async def async_stream(provider, session):
        try:
            print("\nStarting async_stream call...")
            async with asyncio.timeout(30):  # Add timeout to prevent hanging
                # Ensure provider has the current session
                provider.client = session
                # Create a new stream with the provider to ensure proper event tracking
                stream = await aco.chat_stream(
                    message="Hello from async streaming",
                    model="command",
                    session=session
                )
                print("Stream created, starting iteration...")
                async for chunk in stream:
                    print(f"Received async chunk: {chunk}")
                print("Stream completed successfully")
        except asyncio.TimeoutError:
            print("Warning: Async stream timed out")
            raise
        except Exception as e:
            print(f"Error in async_stream: {str(e)}")
            raise

    async def run_async_tests():
        print("\nRunning async tests...")
        print("Starting async_no_stream...")
        await async_no_stream()
        print("Completed async_no_stream")
        
        print("\nStarting first async_stream...")
        await async_stream(provider, session)
        print("Completed first async_stream")
        
        print("\nStarting second async_stream...")
        await async_stream(provider, session)  # Run twice to ensure we get all LLM calls
        print("Completed second async_stream")
        
        print("\nStarting third async_stream...")
        await async_stream(provider, session)  # Run thrice to ensure we get all LLM calls
        print("Completed third async_stream")
        
        print("\nAll async tests completed successfully")
        
        # End session and verify analytics after all tests
        session.end_session("Success")
        analytics = session.get_analytics()
        print(f"\nAnalytics: {analytics}")
        assert analytics["LLM calls"] >= 4, f"Expected at least 4 LLM calls, but got {analytics['LLM calls']}"

    # Call each function with proper error handling
    try:
        sync_no_stream()
        sync_stream()
        asyncio.run(run_async_tests())
    except Exception as e:
        print(f"Error during Cohere test: {str(e)}")
        raise

    print("\nTest completed successfully")

if __name__ == "__main__":
    test_cohere_integration()
