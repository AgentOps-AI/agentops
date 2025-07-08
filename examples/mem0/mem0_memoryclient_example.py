"""
# Cloud Memory Operations with Mem0 MemoryClient

This example demonstrates how to use Mem0's cloud-based MemoryClient for managing conversational memory and user preferences with both synchronous and asynchronous operations.

## Overview

This example showcases cloud-based memory management operations where we:

1. **Initialize MemoryClient instances** for both sync and async cloud operations
2. **Store conversation history** in the cloud with rich metadata
3. **Perform concurrent operations** using async/await patterns
4. **Search and filter memories** using natural language and structured queries

By using the cloud-based MemoryClient with async operations, you can leverage Mem0's managed infrastructure while performing multiple memory operations simultaneously. This is ideal for production applications that need scalable memory management without managing local storage.
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Set environment variables before importing
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
mem0_api_key = os.getenv("MEM0_API_KEY")

# Import agentops BEFORE mem0 to ensure proper instrumentation
import agentops  # noqa  E402

# Now import mem0 - it will be instrumented by agentops
from mem0 import MemoryClient, AsyncMemoryClient  # noqa  E402


def demonstrate_sync_memory_client(sample_messages, sample_preferences, user_id):
    """
    Demonstrate synchronous MemoryClient operations with cloud storage.

    This function performs sequential cloud memory operations including:
    - Initializing cloud-based memory client with API authentication
    - Adding conversation messages to cloud storage
    - Storing user preferences with metadata
    - Searching memories using natural language
    - Retrieving memories with filters
    - Cleaning up cloud memories

    Args:
        sample_messages: List of conversation messages to store
        sample_preferences: List of user preferences to store
        user_id: Unique identifier for the user

    Cloud benefit: All memory operations are handled by Mem0's infrastructure,
    providing scalability and persistence without local storage management.
    """
    agentops.start_trace("Mem0 MemoryClient Example", tags=["mem0_memoryclient_example"])
    try:
        # Initialize sync MemoryClient with API key for cloud access
        client = MemoryClient(api_key=mem0_api_key)

        # Add conversation to cloud storage with metadata
        result = client.add(
            sample_messages, user_id=user_id, metadata={"category": "cloud_movie_preferences", "session": "cloud_demo"}
        )
        print(f"Add result: {result}")

        # Add preferences sequentially to cloud
        for i, preference in enumerate(sample_preferences[:3]):  # Limit for demo
            result = client.add(preference, user_id=user_id, metadata={"type": "cloud_preference", "index": i})

        # 2. SEARCH operations - leverage cloud search capabilities
        search_result = client.search("What are the user's movie preferences?", user_id=user_id)
        print(f"Search result: {search_result}")

        # 3. GET_ALL with filters - demonstrate structured query capabilities
        filters = {"AND": [{"user_id": user_id}]}
        all_memories = client.get_all(filters=filters, limit=10)
        print(f"Cloud memories retrieved: {all_memories}")

        # Cleanup - remove all user memories from cloud
        delete_all_result = client.delete_all(user_id=user_id)
        print(f"Delete all result: {delete_all_result}")
        agentops.end_trace(end_state="success")
    except Exception:
        agentops.end_trace(end_state="error")


async def demonstrate_async_memory_client(sample_messages, sample_preferences, user_id):
    """
    Demonstrate asynchronous MemoryClient operations with concurrent cloud access.

    This function performs concurrent cloud memory operations including:
    - Initializing async cloud-based memory client
    - Adding multiple memories concurrently using asyncio.gather()
    - Performing parallel search operations across cloud storage
    - Retrieving filtered memories asynchronously
    - Cleaning up cloud memories efficiently

    Args:
        sample_messages: List of conversation messages to store
        sample_preferences: List of user preferences to store
        user_id: Unique identifier for the user

    Performance benefit: Async operations allow multiple cloud API calls to execute
    concurrently, significantly reducing total execution time compared to sequential calls.
    This is especially beneficial when dealing with network I/O to cloud services.
    """
    agentops.start_trace("Mem0 MemoryClient Async Example", tags=["mem0_memoryclient_example"])
    try:
        # Initialize async MemoryClient for concurrent cloud operations
        async_client = AsyncMemoryClient(api_key=mem0_api_key)

        # Add conversation and preferences concurrently to cloud
        add_conversation_task = async_client.add(
            sample_messages, user_id=user_id, metadata={"category": "async_cloud_movies", "session": "async_cloud_demo"}
        )

        # Create tasks for adding preferences in parallel
        add_preference_tasks = [
            async_client.add(pref, user_id=user_id, metadata={"type": "async_cloud_preference", "index": i})
            for i, pref in enumerate(sample_preferences[:3])
        ]

        # Execute all add operations concurrently
        results = await asyncio.gather(add_conversation_task, *add_preference_tasks)
        for i, result in enumerate(results):
            print(f"{i + 1}. {result}")

        # 2. Concurrent SEARCH operations - multiple cloud searches in parallel
        search_tasks = [
            async_client.search("movie preferences", user_id=user_id),
            async_client.search("food preferences", user_id=user_id),
            async_client.search("work information", user_id=user_id),
        ]

        # Execute all searches concurrently
        search_results = await asyncio.gather(*search_tasks)
        for i, result in enumerate(search_results):
            print(f"Search {i + 1} result: {result}")

        # 3. GET_ALL operation - retrieve filtered memories from cloud
        filters = {"AND": [{"user_id": user_id}]}
        all_memories = await async_client.get_all(filters=filters, limit=10)
        print(f"Async cloud memories: {all_memories}")

        # Final cleanup - remove all memories asynchronously
        delete_all_result = await async_client.delete_all(user_id=user_id)
        print(f"Delete all result: {delete_all_result}")

        agentops.end_trace(end_state="success")

    except Exception:
        agentops.end_trace(end_state="error")


# Sample user data for demonstration
user_id = "alice_demo"
agent_id = "assistant_demo"
run_id = "session_001"

# Sample conversation data demonstrating preference discovery through dialogue
sample_messages = [
    {"role": "user", "content": "I'm planning to watch a movie tonight. Any recommendations?"},
    {"role": "assistant", "content": "How about a thriller? They can be quite engaging."},
    {"role": "user", "content": "I'm not a big fan of thriller movies but I love sci-fi movies."},
    {
        "role": "assistant",
        "content": "Got it! I'll avoid thriller recommendations and suggest sci-fi movies in the future.",
    },
]

# Sample user preferences representing various personal attributes
sample_preferences = [
    "I prefer dark roast coffee over light roast",
    "I exercise every morning at 6 AM",
    "I'm vegetarian and avoid all meat products",
    "I love reading science fiction novels",
    "I work in software engineering",
]

# Execute both sync and async demonstrations
# Note: The async version typically completes faster due to concurrent operations
demonstrate_sync_memory_client(sample_messages, sample_preferences, user_id)
asyncio.run(demonstrate_async_memory_client(sample_messages, sample_preferences, user_id))

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=None)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise
