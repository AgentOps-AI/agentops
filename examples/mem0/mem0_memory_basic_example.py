"""
Basic Memory Operations with Mem0: Local vs Cloud

This example demonstrates the two primary ways to use Mem0 for memory management:
1. Memory class - For local, self-hosted memory storage
2. MemoryClient class - For cloud-based memory storage using Mem0's managed service

Both approaches offer the same core functionality (add, search, get_all) but differ in:
- Storage location: Local vs Mem0's cloud infrastructure
- Setup requirements: Local configuration vs API key authentication
- Use cases: Development/self-hosted vs production/scalable applications

Key features demonstrated:
- Adding individual memories with metadata
- Storing conversation history
- Searching memories using natural language
- Retrieving all memories for a user

This example runs both approaches sequentially to showcase the similarities and differences.
"""

import os
from dotenv import load_dotenv
from mem0 import Memory, MemoryClient
import agentops

# Load environment variables from .env file
load_dotenv()

# Set up API keys for AgentOps tracing
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
api_key = os.getenv("MEM0_API_KEY")

# Configuration for Memory with OpenAI as the LLM provider
# This configuration specifies which model to use and its parameters
openai_config = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4o-mini",
            "temperature": 0.1,  # Low temperature for consistent outputs
            "max_tokens": 2000,
            "api_key": os.getenv("OPENAI_API_KEY"),
        },
    }
}

# Sample conversation data demonstrating user preferences
# This shows how Mem0 can extract and remember information from natural dialogue
test_messages = [
    {"role": "user", "content": "I love science fiction movies and books."},
    {"role": "assistant", "content": "That's great! Sci-fi offers amazing worlds and concepts."},
    {"role": "user", "content": "I also prefer dark roast coffee over light roast."},
]

# Start AgentOps trace for monitoring and debugging
agentops.start_trace("mem0_memory_basic_example", tags=["mem0_memory_basic_example"])
try:
    # Initialize Memory instance with the OpenAI configuration
    # This creates a local memory store that processes and stores memories on your infrastructure
    m_sync = Memory.from_config(openai_config)

    # This demonstrates storing individual facts with metadata
    result = m_sync.add(
        [{"role": "user", "content": "I like to drink coffee in the morning and go for a walk."}],
        user_id="alice_sync",
        metadata={"category": "preferences", "type": "sync"},
    )

    # This shows how to store entire conversations that Mem0 will analyze for memorable information
    result = m_sync.add(test_messages, user_id="alice_sync", metadata={"category": "conversation", "type": "sync"})

    # Demonstrates how to query stored memories with questions
    search_result = m_sync.search("What does the user like to drink?", user_id="alice_sync")

    # Shows how to get a complete view of what Mem0 remembers about a user
    all_memories = m_sync.get_all(user_id="alice_sync")

    # Display all memories for inspection
    if all_memories.get("results"):
        for i, memory in enumerate(all_memories["results"], 1):
            print(f"{i}. {memory.get('memory', 'N/A')}")

    # Successfully completed all operations
    agentops.end_trace(end_state="success")

except Exception:
    # Log any errors that occur during execution
    agentops.end_trace(end_state="error")


# Start AgentOps trace for monitoring and debugging
agentops.start_trace("mem0_memoryclient_basic_example", tags=["mem0_memoryclient_basic_example"])
try:
    # Initialize MemoryClient with API key for cloud access
    # This connects to Mem0's cloud infrastructure for scalable memory management
    m_sync = MemoryClient(api_key=api_key)

    # This demonstrates storing individual facts with metadata
    result = m_sync.add(
        [{"role": "user", "content": "I like to drink coffee in the morning and go for a walk."}],
        user_id="alice_sync",
        metadata={"category": "preferences", "type": "sync"},
    )

    # This shows how to store entire conversations that Mem0 will analyze for memorable information
    result = m_sync.add(
        test_messages,
        user_id="alice_sync",
    )
    filters = {
        "AND": [
            {"user_id": user_id},
        ]
    }
    # Demonstrates how to query stored memories with questions
    search_result = m_sync.search(version="v2", query="What does the user like to drink?", filters=filters)
    print(f"Cloud search results: {search_result}")

    # Shows how to get all memories stored in Mem0's cloud for a user
    all_memories = m_sync.get_all(version="v2", filters=filters, page_size=1)
    print(f"Total cloud memories: {len(all_memories.get('results', []))}")

    # Display all memories for inspection
    if all_memories.get("results"):
        for i, memory in enumerate(all_memories["results"], 1):
            print(f"{i}. {memory.get('memory', 'N/A')}")

    # Successfully completed all operations
    agentops.end_trace(end_state="success")
except Exception:
    # Log any errors that occur during execution
    agentops.end_trace(end_state="error")
