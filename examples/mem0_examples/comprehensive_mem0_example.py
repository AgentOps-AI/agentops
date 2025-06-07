"""
Comprehensive Mem0 Example with AgentOps Instrumentation

This example demonstrates all four mem0 memory classes:
1. Memory (sync local memory)
2. AsyncMemory (async local memory)  
3. MemoryClient (sync cloud client)
4. AsyncMemoryClient (async cloud client)

Each section shows CRUD operations and demonstrates AgentOps instrumentation.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# CRITICAL: Initialize AgentOps BEFORE importing mem0 classes
# This ensures proper instrumentation and context propagation
import agentops  # noqa: E402

# Initialize AgentOps FIRST
agentops.init(os.getenv("AGENTOPS_API_KEY"))

# Now import mem0 classes AFTER agentops initialization
from mem0 import Memory, AsyncMemory, MemoryClient, AsyncMemoryClient  # noqa: E402

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration for local memory (Memory and AsyncMemory)
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

# API key for cloud clients (MemoryClient and AsyncMemoryClient)
mem0_api_key = os.getenv("MEM0_API_KEY")

# Sample user data
user_id = "alice_demo"
agent_id = "assistant_demo"
run_id = "session_001"

# Sample conversation data
sample_messages = [
    {"role": "user", "content": "I'm planning to watch a movie tonight. Any recommendations?"},
    {"role": "assistant", "content": "How about a thriller? They can be quite engaging."},
    {"role": "user", "content": "I'm not a big fan of thriller movies but I love sci-fi movies."},
    {
        "role": "assistant",
        "content": "Got it! I'll avoid thriller recommendations and suggest sci-fi movies in the future.",
    },
]

sample_preferences = [
    "I prefer dark roast coffee over light roast",
    "I exercise every morning at 6 AM",
    "I'm vegetarian and avoid all meat products",
    "I love reading science fiction novels",
    "I work in software engineering",
]


def demonstrate_sync_memory():
    """Demonstrate sync Memory class operations."""
    print("\n" + "=" * 60)
    print("🧠 SYNC MEMORY (Local) OPERATIONS")
    print("=" * 60)

    try:
        # Initialize sync Memory
        memory = Memory.from_config(local_config)
        print("✅ Sync Memory initialized successfully")

        # 1. ADD operations
        print("\n📝 Adding memories...")

        # Add conversation messages
        result = memory.add(
            sample_messages, user_id=user_id, metadata={"category": "movie_preferences", "session": "demo"}
        )
        print(f"   📌 Added conversation: {result}")

        # Add individual preferences
        for i, preference in enumerate(sample_preferences):
            result = memory.add(preference, user_id=user_id, metadata={"type": "preference", "index": i})
            print(f"   📌 Added preference {i+1}: {result}")

        # 2. SEARCH operations
        print("\n🔍 Searching memories...")
        search_queries = [
            "What movies does the user like?",
            "What are the user's food preferences?",
            "When does the user exercise?",
        ]

        for query in search_queries:
            results = memory.search(query, user_id=user_id)
            print(f"   🔎 Query: '{query}'")
            if results and "results" in results:
                for j, result in enumerate(results["results"][:2]):  # Show top 2
                    print(f"      💡 Result {j+1}: {result.get('memory', 'N/A')}")
            else:
                print("      ❌ No results found")

        # 3. GET_ALL operations
        print("\n📋 Getting all memories...")
        all_memories = memory.get_all(user_id=user_id)
        if all_memories and "results" in all_memories:
            print(f"   📊 Total memories: {len(all_memories['results'])}")
            for i, mem in enumerate(all_memories["results"][:3]):  # Show first 3
                print(f"      {i+1}. ID: {mem.get('id', 'N/A')[:8]}... | {mem.get('memory', 'N/A')[:50]}...")

        # Cleanup
        print("\n🧹 Cleaning up all memories...")
        delete_all_result = memory.delete_all(user_id=user_id)
        print(f"   ✅ Delete all result: {delete_all_result}")

    except Exception as e:
        print(f"❌ Sync Memory error: {e}")
        logger.error(f"Sync Memory demonstration failed: {e}")


async def demonstrate_async_memory():
    """Demonstrate async Memory class operations."""
    print("\n" + "=" * 60)
    print("🚀 ASYNC MEMORY (Local) OPERATIONS")
    print("=" * 60)

    try:
        # Initialize async Memory
        async_memory = AsyncMemory.from_config(local_config)
        print("✅ Async Memory initialized successfully")

        # 1. ADD operations
        print("\n📝 Adding memories asynchronously...")

        # Add conversation messages
        result = await async_memory.add(
            sample_messages, user_id=user_id, metadata={"category": "async_movie_preferences", "session": "async_demo"}
        )
        print(f"   📌 Added conversation: {result}")

        # Add preferences concurrently
        async def add_preference(preference, index):
            return await async_memory.add(
                preference, user_id=user_id, metadata={"type": "async_preference", "index": index}
            )

        tasks = [add_preference(pref, i) for i, pref in enumerate(sample_preferences)]
        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            print(f"   📌 Added async preference {i+1}: {result}")

        # 2. SEARCH operations
        print("\n🔍 Searching memories asynchronously...")
        search_queries = [
            "What movies does the user like?",
            "What are the user's dietary restrictions?",
            "What does the user do for work?",
        ]

        async def search_memory(query):
            return await async_memory.search(query, user_id=user_id), query

        search_tasks = [search_memory(query) for query in search_queries]
        search_results = await asyncio.gather(*search_tasks)

        for result, query in search_results:
            print(f"   🔎 Query: '{query}'")
            if result and "results" in result:
                for j, res in enumerate(result["results"][:2]):
                    print(f"      💡 Result {j+1}: {res.get('memory', 'N/A')}")
            else:
                print("      ❌ No results found")

        # 3. GET_ALL operations
        print("\n📋 Getting all memories asynchronously...")
        all_memories = await async_memory.get_all(user_id=user_id)
        if all_memories and "results" in all_memories:
            print(f"   📊 Total async memories: {len(all_memories['results'])}")
            for i, mem in enumerate(all_memories["results"][:3]):
                print(f"      {i+1}. ID: {mem.get('id', 'N/A')[:8]}... | {mem.get('memory', 'N/A')[:50]}...")

        # Cleanup
        print("\n🧹 Cleaning up all async memories...")
        delete_all_result = await async_memory.delete_all(user_id=user_id)
        print(f"   ✅ Delete all result: {delete_all_result}")

    except Exception as e:
        print(f"❌ Async Memory error: {e}")
        logger.error(f"Async Memory demonstration failed: {e}")


def demonstrate_sync_memory_client():
    """Demonstrate sync MemoryClient class operations."""
    print("\n" + "=" * 60)
    print("☁️ SYNC MEMORY CLIENT (Cloud) OPERATIONS")
    print("=" * 60)

    if not mem0_api_key:
        print("❌ MEM0_API_KEY not found. Skipping cloud client operations.")
        return

    try:
        # Initialize sync MemoryClient
        client = MemoryClient(api_key=mem0_api_key)
        print("✅ Sync MemoryClient initialized successfully")

        # 1. ADD operations
        print("\n📝 Adding memories to cloud...")

        # Add conversation
        result = client.add(
            sample_messages, user_id=user_id, metadata={"category": "cloud_movie_preferences", "session": "cloud_demo"}
        )
        print(f"   📌 Added conversation to cloud: {result}")

        # Add preferences
        for i, preference in enumerate(sample_preferences[:3]):  # Limit for demo
            result = client.add(preference, user_id=user_id, metadata={"type": "cloud_preference", "index": i})
            print(f"   📌 Added cloud preference {i+1}: {result}")

        # 2. SEARCH operations
        print("\n🔍 Searching cloud memories...")
        search_result = client.search("What are the user's movie preferences?", user_id=user_id)
        print(f"   🔎 Search result: {search_result}")

        # 3. GET_ALL with filters
        print("\n📋 Getting all cloud memories with filters...")
        filters = {"AND": [{"user_id": user_id}]}
        all_memories = client.get_all(filters=filters, limit=10)
        print(f"   📊 Cloud memories retrieved: {all_memories}")

        # Cleanup
        print("\n🧹 Cleaning up cloud memories...")
        delete_all_result = client.delete_all(user_id=user_id)
        print(f"   ✅ Delete all result: {delete_all_result}")

    except Exception as e:
        print(f"❌ Sync MemoryClient error: {e}")
        logger.error(f"Sync MemoryClient demonstration failed: {e}")


async def demonstrate_async_memory_client():
    """Demonstrate async MemoryClient class operations."""
    print("\n" + "=" * 60)
    print("🌐 ASYNC MEMORY CLIENT (Cloud) OPERATIONS")
    print("=" * 60)

    if not mem0_api_key:
        print("❌ MEM0_API_KEY not found. Skipping async cloud client operations.")
        return

    try:
        # Initialize async MemoryClient
        async_client = AsyncMemoryClient(api_key=mem0_api_key)
        print("✅ Async MemoryClient initialized successfully")

        # 1. ADD operations concurrently
        print("\n📝 Adding memories to cloud asynchronously...")

        # Add conversation and preferences concurrently
        add_conversation_task = async_client.add(
            sample_messages, user_id=user_id, metadata={"category": "async_cloud_movies", "session": "async_cloud_demo"}
        )

        add_preference_tasks = [
            async_client.add(pref, user_id=user_id, metadata={"type": "async_cloud_preference", "index": i})
            for i, pref in enumerate(sample_preferences[:3])
        ]

        results = await asyncio.gather(add_conversation_task, *add_preference_tasks)
        print(f"   📌 Added conversation and preferences: {len(results)} items")
        for i, result in enumerate(results):
            print(f"      {i+1}. {result}")

        # 2. Concurrent SEARCH operations
        print("\n🔍 Performing concurrent searches...")
        search_tasks = [
            async_client.search("movie preferences", user_id=user_id),
            async_client.search("food preferences", user_id=user_id),
            async_client.search("work information", user_id=user_id),
        ]

        search_results = await asyncio.gather(*search_tasks)
        for i, result in enumerate(search_results):
            print(f"   🔎 Search {i+1} result: {result}")

        # 3. GET_ALL operation
        print("\n📋 Getting all async cloud memories...")
        filters = {"AND": [{"user_id": user_id}]}
        all_memories = await async_client.get_all(filters=filters, limit=10)
        print(f"   📊 Async cloud memories: {all_memories}")

        # Final cleanup
        print("\n🧹 Final cleanup of async cloud memories...")
        delete_all_result = await async_client.delete_all(user_id=user_id)
        print(f"   ✅ Delete all result: {delete_all_result}")

    except Exception as e:
        print(f"❌ Async MemoryClient error: {e}")
        logger.error(f"Async MemoryClient demonstration failed: {e}")


def check_environment():
    """Check if required environment variables are set."""
    required_vars = ["AGENTOPS_API_KEY", "OPENAI_API_KEY"]
    optional_vars = ["MEM0_API_KEY"]

    missing_required = [var for var in required_vars if not os.getenv(var)]
    missing_optional = [var for var in optional_vars if not os.getenv(var)]

    if missing_required:
        print(f"❌ Missing required environment variables: {missing_required}")
        return False

    if missing_optional:
        print(f"⚠️ Missing optional environment variables: {missing_optional}")
        print("   Cloud client operations will be skipped.")

    return True


async def main():
    """Run the complete demonstration of all mem0 classes."""
    print("🎬 STARTING COMPREHENSIVE MEM0 DEMONSTRATION")
    print("This demo showcases all four mem0 classes with AgentOps instrumentation:")
    print("1. Memory (sync local)")
    print("2. AsyncMemory (async local)")
    print("3. MemoryClient (sync cloud)")
    print("4. AsyncMemoryClient (async cloud)")
    print("\n" + "=" * 80)

    if not check_environment():
        print("Please set the required environment variables and try again.")
        return

    try:
        # Run all demonstrations
        demonstrate_sync_memory()
        await demonstrate_async_memory()
        demonstrate_sync_memory_client()
        await demonstrate_async_memory_client()

        print("\n" + "=" * 80)
        print("✅ COMPREHENSIVE MEM0 DEMONSTRATION COMPLETED!")
        print("Check your AgentOps dashboard to see the instrumentation data.")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"❌ Demo failed: {e}")

    finally:
        # End AgentOps session
        agentops.end_session("Success")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
