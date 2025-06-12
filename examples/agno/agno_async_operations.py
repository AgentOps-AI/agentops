"""
Async Operations with Agno

This script demonstrates concurrent execution of multiple AI agent tasks using Python's asyncio.
Instead of sequential execution where each task waits for the previous one to complete,
async operations allow multiple tasks to run concurrently, significantly improving performance
when dealing with I/O-bound operations like API calls to AI models.
"""

import os
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
import asyncio  # For concurrent task execution
import agentops  # For tracking AI operations and analytics
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize AgentOps for monitoring AI usage, costs, and performance
agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

# Configuration
MODEL_ID = "gpt-4o-mini"  # Cost-effective OpenAI model suitable for most tasks

def check_environment():
    """
    Validate that required API keys are properly configured.
    
    Returns:
        bool: True if all required environment variables are set
    """
    required_vars = ["AGENTOPS_API_KEY", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Missing required environment variables: {missing_vars}")
        print("Please configure these in your .env file:")
        for var in missing_vars:
            print(f"  {var}=your_key_here")
        return False

    print("✓ Environment variables configured successfully")
    return True


async def demonstrate_async_operations():
    """
    Demonstrate concurrent execution of multiple AI agent tasks.
    
    This function creates multiple async tasks that execute concurrently rather than sequentially.
    Each task makes an independent API call to the AI model, and asyncio.gather() 
    waits for all tasks to complete before returning results.
    
    Performance benefit: Instead of 3 sequential calls taking ~90 seconds total,
    concurrent execution typically completes in ~30 seconds.
    """
    print("\n" + "=" * 60)
    print("CONCURRENT AI OPERATIONS DEMO")
    print("=" * 60)

    try:
        # Initialize AI agent with specified model
        print("Initializing AI agent...")
        agent = Agent(model=OpenAIChat(id=MODEL_ID))
        print("✓ Agent ready")

        # Define async task functions
        # Each function is a coroutine that can be executed concurrently
        
        async def task1():
            """Query AI about Python programming language."""
            print("→ Starting Python explanation task...")
            response = await agent.arun("Explain Python programming language in one paragraph")
            return f"Python: {response.content}"

        async def task2():
            """Query AI about JavaScript programming language."""
            print("→ Starting JavaScript explanation task...")
            response = await agent.arun("Explain JavaScript programming language in one paragraph")
            return f"JavaScript: {response.content}"

        async def task3():
            """Query AI for comparison between programming languages."""
            print("→ Starting comparison task...")
            response = await agent.arun("Compare Python and JavaScript briefly")
            return f"Comparison: {response.content}"

        # Execute all tasks concurrently using asyncio.gather()
        # This is the key to async performance - tasks run simultaneously
        print("\nExecuting tasks concurrently...")
        results = await asyncio.gather(task1(), task2(), task3())

        # Process and display results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        
        for i, result in enumerate(results, 1):
            print(f"\nTask {i} Result:")
            print(result)
            print("-" * 50)

    except Exception as e:
        print(f"Error during async operations: {e}")
        print("This may be due to API rate limits, network issues, or authentication problems")


async def main():
    """
    Main async function that orchestrates the demonstration.
    
    Handles environment validation and executes the async operations demo
    with proper error handling and user feedback.
    """
    print("Agno Async Operations Demonstration")
    print("Showcasing concurrent AI task execution for improved performance")
    print()
    
    # Validate environment setup
    if not check_environment():
        print("Cannot proceed without proper API configuration")
        return

    print("\nStarting async operations demo...")

    # Execute async operations demonstration
    try:
        await demonstrate_async_operations()
        print("\n✓ Demo completed successfully")
        print("Note: Observe the performance improvement compared to sequential execution")
        
    except Exception as e:
        print(f"Demo execution failed: {e}")
        print("Check your API keys, rate limits, and network connectivity")


if __name__ == "__main__":
    """
    Entry point for the script.
    
    Uses asyncio.run() to execute the main async function and handle
    the async event loop lifecycle automatically.
    """
    asyncio.run(main())
