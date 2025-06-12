"""
Workflow Setup with Caching in Agno

This example demonstrates how to create custom workflows that can:
- Orchestrate complex agent interactions
- Implement caching for improved performance
- Maintain session state across multiple runs
- Stream responses efficiently

Workflows are powerful abstractions that allow you to build reusable,
stateful agent pipelines with custom logic and optimizations.
"""

import os
from agno.agent import Agent, RunResponse
import asyncio
import agentops
from dotenv import load_dotenv
from agno.workflow import Workflow
from agno.utils.pprint import pprint_run_response
from agno.models.openai import OpenAIChat
from agno.utils.log import logger
from typing import Iterator

# Load environment variables
load_dotenv()

# Initialize AgentOps for monitoring workflow execution
agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

# Configuration
MODEL_ID = "gpt-4o-mini"  # Default model for agents


def check_environment():
    """
    Verify that all required API keys are properly configured.

    Returns:
        bool: True if all required environment variables are set
    """
    required_vars = ["AGENTOPS_API_KEY", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Missing required environment variables: {missing_vars}")
        print("Please set these in your .env file or environment")
        return False

    print("✓ Environment variables checked successfully")
    return True


class CacheWorkflow(Workflow):
    """
    A workflow that demonstrates intelligent caching capabilities.

    This workflow:
    - Caches agent responses to avoid redundant API calls
    - Maintains session state across multiple invocations
    - Provides instant responses for repeated queries
    - Reduces costs and improves performance

    Use cases:
    - FAQ systems where questions repeat frequently
    - Development/testing to avoid repeated API calls
    - Systems with predictable query patterns
    """

    # Workflow metadata (descriptive, not functional)
    description: str = "A workflow that caches previous outputs for efficiency"

    # Initialize agents as workflow attributes
    # This agent will be used to generate responses when cache misses occur
    agent = Agent(model=OpenAIChat(id=MODEL_ID), description="General purpose agent for generating responses")

    def run(self, message: str) -> Iterator[RunResponse]:
        """
        Execute the workflow with caching logic.

        This method:
        1. Checks if the response is already cached
        2. Returns cached response immediately if found
        3. Generates new response if not cached
        4. Caches the new response for future use

        Args:
            message: The input query to process

        Yields:
            RunResponse: Streamed response chunks
        """
        logger.info(f"Checking cache for '{message}'")

        # Check if we've already processed this exact message
        # session_state persists across workflow runs
        if self.session_state.get(message):
            logger.info(f"Cache hit for '{message}'")
            # Return cached response immediately (no API call needed)
            yield RunResponse(run_id=self.run_id, content=self.session_state.get(message))
            return

        # Cache miss - need to generate new response
        logger.info(f"Cache miss for '{message}'")

        # Run the agent and stream the response
        # Using stream=True for real-time output
        yield from self.agent.run(message, stream=True)

        # After streaming completes, cache the full response
        # This makes future requests for the same message instant
        self.session_state[message] = self.agent.run_response.content
        logger.info("Cached response for future use")


def demonstrate_workflows():
    """
    Demonstrate workflow capabilities with caching.

    This function shows:
    - How to create and use custom workflows
    - The performance benefits of caching
    - Session state persistence
    - Response streaming
    """
    print("\n" + "=" * 60)
    print("WORKFLOWS WITH INTELLIGENT CACHING")
    print("=" * 60)

    try:
        # Create an instance of our caching workflow
        print("\n1. Creating CacheWorkflow instance...")
        workflow = CacheWorkflow()
        print("   ✓ Workflow initialized with caching capabilities")

        # First run - this will be a cache miss
        print("\n2. First run (expecting cache miss):")
        print("   This will make an API call and take ~1-2 seconds")

        # Run workflow with a test message
        response: Iterator[RunResponse] = workflow.run(message="Tell me a joke.")

        # Pretty print the response with timing information
        pprint_run_response(response, markdown=True, show_time=True)

        # Second run - this should be a cache hit
        print("\n3. Second run (expecting cache hit):")
        print("   This should return instantly from cache")

        # Run workflow with the same message
        response: Iterator[RunResponse] = workflow.run(message="Tell me a joke.")

        # Pretty print the response - notice the instant response time
        pprint_run_response(response, markdown=True, show_time=True)

        print("\n✓ Workflow demonstration completed")
        print("\nNotice the performance difference:")
        print("- First run: Makes API call, takes time")
        print("- Second run: Returns from cache instantly")
        print("- Same content, but much faster delivery")

    except Exception as e:
        print(f"\nError during workflow demonstration: {e}")
        print("This might be due to API issues or configuration problems")


async def main():
    """
    Main function that orchestrates the workflow demonstration.

    This async function handles:
    - Environment validation
    - Running the workflow demonstration
    - Error handling and user feedback
    """
    print("Welcome to Agno Workflow Demo")
    print("This demo showcases custom workflows with caching capabilities")
    print()

    # Validate environment setup
    if not check_environment():
        print("Cannot proceed without proper API configuration")
        return

    # Run demonstration
    print("\nStarting workflow demonstration...")

    try:
        demonstrate_workflows()
        print("\n\n✓ Workflow demo completed successfully!")
        print("\nKey Takeaways:")
        print("- Workflows enable custom agent orchestration")
        print("- Caching dramatically improves performance")
        print("- Session state persists across runs")
        print("- Streaming responses provide real-time feedback")
        print("- AgentOps tracks all workflow executions")

    except Exception as e:
        print(f"Demo failed: {e}")
        print("Please check your API keys and network connection")


if __name__ == "__main__":
    """
    Entry point for the script.
    
    Uses asyncio to run the main function, maintaining consistency
    with other examples and preparing for async operations.
    """
    asyncio.run(main())
