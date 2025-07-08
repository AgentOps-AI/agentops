"""
# Memory Operations with Mem0

This example demonstrates how to use Mem0's memory management capabilities with both synchronous and asynchronous operations to store, search, and manage conversational context and user preferences.

## Overview

This example showcases practical memory management operations where we:

1. **Initialize Mem0 Memory instances** for both sync and async operations
2. **Store conversation history** and user preferences with metadata
3. **Search memories** using natural language queries
4. **Compare performance** between synchronous and asynchronous memory operations

By using async operations, you can perform multiple memory operations simultaneously instead of waiting for each one to complete sequentially. This is particularly beneficial when dealing with multiple memory additions or searches.
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Enable debug logging for AgentOps
os.environ["AGENTOPS_LOG_LEVEL"] = "DEBUG"

# Set environment variables before importing
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

# Now import mem0 - it will be instrumented by agentops
from mem0 import Memory, AsyncMemory  # noqa  E402

# Import agentops BEFORE mem0 to ensure proper instrumentation
import agentops  # noqa  E402


def demonstrate_sync_memory(local_config, sample_messages, sample_preferences, user_id):
    """
    Demonstrate synchronous Memory class operations.

    This function performs sequential memory operations including:
    - Adding conversation messages with metadata
    - Storing individual user preferences
    - Searching memories using natural language queries
    - Retrieving all memories for a user
    - Cleaning up memories after demonstration

    Args:
        local_config: Configuration dict for Memory initialization
        sample_messages: List of conversation messages to store
        sample_preferences: List of user preferences to store
        user_id: Unique identifier for the user

    Performance note: Sequential operations take longer as each operation
    must complete before the next one begins.
    """

    tracer = agentops.start_trace("Mem0 Memory Example", tags=["mem0_memory_example"])
    try:
        # Initialize sync Memory with local configuration
        memory = Memory.from_config(local_config)

        # Add conversation messages with metadata for categorization
        result = memory.add(
            sample_messages, user_id=user_id, metadata={"category": "movie_preferences", "session": "demo"}
        )

        # Add individual preferences sequentially
        for i, preference in enumerate(sample_preferences):
            result = memory.add(preference, user_id=user_id, metadata={"type": "preference", "index": i})

        # 2. SEARCH operations - demonstrate natural language search capabilities
        search_queries = [
            "What movies does the user like?",
            "What are the user's food preferences?",
            "When does the user exercise?",
        ]

        for query in search_queries:
            results = memory.search(query, user_id=user_id)

            if results and "results" in results:
                for j, result in enumerate(results["results"][:2]):  # Show top 2
                    print(f"Result {j + 1}: {result.get('memory', 'N/A')}")
            else:
                print("No results found")

        # 3. GET_ALL operations - retrieve all memories for the user
        all_memories = memory.get_all(user_id=user_id)
        if all_memories and "results" in all_memories:
            print(f"Total memories: {len(all_memories['results'])}")

        # Cleanup - remove all memories for the user
        delete_all_result = memory.delete_all(user_id=user_id)
        print(f"Delete all result: {delete_all_result}")

        agentops.end_trace(tracer, end_state="Success")
    except Exception as e:
        agentops.end_trace(tracer, end_state="Error")
        raise e


async def demonstrate_async_memory(local_config, sample_messages, sample_preferences, user_id):
    """
    Demonstrate asynchronous Memory class operations with concurrent execution.

    This function performs concurrent memory operations including:
    - Adding conversation messages asynchronously
    - Storing multiple preferences concurrently using asyncio.gather()
    - Performing parallel search operations
    - Retrieving all memories asynchronously
    - Cleaning up memories after demonstration

    Args:
        local_config: Configuration dict for AsyncMemory initialization
        sample_messages: List of conversation messages to store
        sample_preferences: List of user preferences to store
        user_id: Unique identifier for the user

    Performance benefit: Concurrent operations significantly reduce total execution time
    by running multiple memory operations in parallel.
    """

    tracer = agentops.start_trace("Mem0 Memory Async Example", tags=["mem0", "async", "memory-management"])
    try:
        # Initialize async Memory with configuration
        async_memory = await AsyncMemory.from_config(local_config)

        # 1. ADD operation - store conversation with async context
        # Add conversation messages
        result = await async_memory.add(
            sample_messages, user_id=user_id, metadata={"category": "async_movie_preferences", "session": "async_demo"}
        )

        # Add preferences concurrently using asyncio.gather()
        async def add_preference(preference, index):
            """Helper function to add a single preference asynchronously."""
            return await async_memory.add(
                preference, user_id=user_id, metadata={"type": "async_preference", "index": index}
            )

        # Create tasks for concurrent execution
        tasks = [add_preference(pref, i) for i, pref in enumerate(sample_preferences)]
        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            print(f"Added async preference {i + 1}: {result}")

        # 2. SEARCH operations - perform multiple searches concurrently
        search_queries = [
            "What movies does the user like?",
            "What are the user's dietary restrictions?",
            "What does the user do for work?",
        ]

        async def search_memory(query):
            """Helper function to perform async memory search."""
            return await async_memory.search(query, user_id=user_id), query

        # Execute all searches concurrently
        search_tasks = [search_memory(query) for query in search_queries]
        search_results = await asyncio.gather(*search_tasks)

        for result, query in search_results:
            if result and "results" in result:
                for j, res in enumerate(result["results"][:2]):
                    print(f"Result {j + 1}: {res.get('memory', 'N/A')}")
            else:
                print("No results found")

        # 3. GET_ALL operations - retrieve all memories asynchronously
        all_memories = await async_memory.get_all(user_id=user_id)
        if all_memories and "results" in all_memories:
            print(f"Total async memories: {len(all_memories['results'])}")

        # Cleanup - remove all memories asynchronously
        delete_all_result = await async_memory.delete_all(user_id=user_id)
        print(f"Delete all result: {delete_all_result}")

        agentops.end_trace(tracer, end_state="Success")

    except Exception as e:
        agentops.end_trace(tracer, end_state="Error")
        raise e


# Initialize AgentOps
agentops.init(trace_name="Mem0 Memory Example", tags=["mem0", "memory-management", "agentops-example"])

# Configuration for local memory (Memory)
# This configuration specifies the LLM provider and model settings
local_config = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4o-mini",
            "temperature": 0.1,
            "max_tokens": 2000,
            "api_key": os.getenv("OPENAI_API_KEY"),
        },
    }
}
# Sample user data
user_id = "alice_demo"
agent_id = "assistant_demo"
run_id = "session_001"

# Sample conversation data demonstrating movie preference discovery
sample_messages = [
    {"role": "user", "content": "I'm planning to watch a movie tonight. Any recommendations?"},
    {"role": "assistant", "content": "How about a thriller? They can be quite engaging."},
    {"role": "user", "content": "I'm not a big fan of thriller movies but I love sci-fi movies."},
    {
        "role": "assistant",
        "content": "Got it! I'll avoid thriller recommendations and suggest sci-fi movies in the future.",
    },
]

# Sample user preferences covering various aspects of daily life
sample_preferences = [
    "I prefer dark roast coffee over light roast",
    "I exercise every morning at 6 AM",
]


# Execute both sync and async demonstrations
demonstrate_sync_memory(local_config, sample_messages, sample_preferences, user_id)
asyncio.run(demonstrate_async_memory(local_config, sample_messages, sample_preferences, user_id))

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    # Note: Using trace_id since we ran multiple traces
    # In a real application, you would store each tracer and validate individually
    result = agentops.validate_trace_spans(check_llm=False)  # Don't check for LLM spans as this uses memory operations
    agentops.print_validation_summary(result)
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise
