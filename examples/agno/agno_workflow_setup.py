"""
# Workflow Setup with Caching in Agno

This example demonstrates how to create efficient, stateful workflows in Agno that orchestrate complex agent interactions while maintaining performance through caching and state management.

## Overview
This example shows how to build reusable agent workflows where we:

1. **Design workflow architecture** with custom logic and agent orchestration
2. **Implement caching mechanisms** to store and reuse expensive computations
3. **Manage session state** to maintain context across multiple interactions
4. **Set up response streaming** for real-time output handling

By using workflows, you can create sophisticated agent pipelines that are both performant and maintainable, with built-in optimizations for repeated operations and long-running sessions.

"""

from agno.agent import Agent, RunResponse
import agentops
from dotenv import load_dotenv
from agno.workflow import Workflow
from agno.utils.pprint import pprint_run_response
from agno.models.openai import OpenAIChat
from agno.utils.log import logger
from typing import Iterator


load_dotenv()
agentops.init(auto_start_session=False, trace_name="Agno Workflow Setup", tags=["agno-example", "workflow-setup"])


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
    agent = Agent(model=OpenAIChat(id="gpt-4o-mini"), description="General purpose agent for generating responses")

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

        if self.session_state.get(message):
            logger.info(f"Cache hit for '{message}'")
            # Return cached response immediately (no API call needed)
            yield RunResponse(run_id=self.run_id, content=self.session_state.get(message))
            return

        logger.info(f"Cache miss for '{message}'")

        yield from self.agent.run(message, stream=True)

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

    tracer = agentops.start_trace(trace_name="Agno Workflow Setup Demonstration")
    try:
        workflow = CacheWorkflow()

        response: Iterator[RunResponse] = workflow.run(message="Tell me a joke.")

        pprint_run_response(response, markdown=True, show_time=True)

        response: Iterator[RunResponse] = workflow.run(message="Tell me a joke.")

        pprint_run_response(response, markdown=True, show_time=True)

        agentops.end_trace(tracer, end_state="Success")

    except Exception:
        agentops.end_trace(tracer, end_state="Error")

    # Let's check programmatically that spans were recorded in AgentOps
    print("\n" + "=" * 50)
    print("Now let's verify that our LLM calls were tracked properly...")
    try:
        agentops.validate_trace_spans(trace_context=tracer)
        print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
    except agentops.ValidationError as e:
        print(f"\n❌ Error validating spans: {e}")
        raise


demonstrate_workflows()
