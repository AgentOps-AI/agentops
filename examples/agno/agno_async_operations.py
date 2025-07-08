"""
# Async Operations with Agno

This notebook demonstrates how to leverage asynchronous programming with Agno agents to execute multiple AI tasks concurrently, significantly improving performance and efficiency.

## Overview

This notebook demonstrates a practical example of concurrent AI operations where we:

1. **Initialize an Agno agent** with OpenAI's GPT-4o-mini model
2. **Create multiple async tasks** that query the AI about different programming languages
3. **Compare performance** between concurrent and sequential execution

By using async operations, you can run multiple AI queries simultaneously instead of waiting for each one to complete sequentially. This is particularly beneficial when dealing with I/O-bound operations like API calls to AI models.
"""

import os
import asyncio
from dotenv import load_dotenv
import agentops
from agno.agent import Agent
from agno.models.openai import OpenAIChat

load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_agentops_api_key_here")

agentops.init(auto_start_session=False, trace_name="Agno Async Operations", tags=["agno-example", "async-operation"])


async def demonstrate_async_operations():
    """
    Demonstrate concurrent execution of multiple AI agent tasks.

    This function creates multiple async tasks that execute concurrently rather than sequentially.
    Each task makes an independent API call to the AI model, and asyncio.gather()
    waits for all tasks to complete before returning results.

    Performance benefit: Instead of 3 sequential calls taking ~90 seconds total,
    concurrent execution typically completes in ~30 seconds.
    """
    tracer = agentops.start_trace(trace_name="Agno Async Operations Example")

    try:
        # Initialize AI agent with specified model
        agent = Agent(model=OpenAIChat(id="gpt-4o-mini"))

        async def task1():
            """Query AI about Python programming language."""
            response = await agent.arun("Explain Python programming language in one paragraph")
            return f"Python: {response.content}"

        async def task2():
            """Query AI about JavaScript programming language."""
            response = await agent.arun("Explain JavaScript programming language in one paragraph")
            return f"JavaScript: {response.content}"

        async def task3():
            """Query AI for comparison between programming languages."""
            response = await agent.arun("Compare Python and JavaScript briefly")
            return f"Comparison: {response.content}"

        # Execute all tasks concurrently using asyncio.gather()
        results = await asyncio.gather(task1(), task2(), task3())

        for i, result in enumerate(results, 1):
            print(f"\nTask {i} Result:")
            print(result)
            print("-" * 50)

        agentops.end_trace(tracer, end_state="Success")

    except Exception as e:
        print(f"An error occurred: {e}")
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


if __name__ == "__main__":
    asyncio.run(demonstrate_async_operations())
