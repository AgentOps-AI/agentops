"""
Async function decorator examples for AgentOps.

This example shows how to use decorators with async functions and
methods for tracing async operations.
"""

import asyncio
import time
from typing import Dict, Any, List

from agentops.sdk.decorators.agentops import (
    session,
    agent,
    tool,
    llm_call,
    workflow_step,
    workflow_task
)


@session(name="async_session")
async def start_async_session():
    """Start an async session."""
    print("Starting async session")
    await asyncio.sleep(0.1)  # Simulate async work
    return {"session_id": f"async_sess_{int(time.time())}", "start_time": time.time()}


@llm_call()
async def async_llm_call(prompt: str) -> str:
    """Make an async LLM API call."""
    print(f"Calling LLM with prompt: {prompt}")
    await asyncio.sleep(0.5)  # Simulate network latency
    return f"LLM response to: {prompt}"


@tool()
async def async_search_tool(query: str) -> Dict[str, Any]:
    """Async search tool implementation."""
    print(f"Searching for: {query}")
    await asyncio.sleep(0.3)  # Simulate search latency
    return {
        "query": query,
        "results": [f"Result {i} for {query}" for i in range(3)],
        "timestamp": time.time()
    }


@agent()
async def async_agent(query: str) -> Dict[str, Any]:
    """Async agent implementation."""
    print(f"Agent processing: {query}")
    
    # Get LLM response
    llm_response = await async_llm_call(f"Process this query: {query}")
    
    # Search for information
    search_results = await async_search_tool(query)
    
    # Combine results
    return {
        "query": query,
        "llm_response": llm_response,
        "search_results": search_results,
        "timestamp": time.time()
    }


@workflow_step(name="process_step")
async def process_data_step(data: List[str]) -> List[str]:
    """A workflow step that processes data."""
    print(f"Processing {len(data)} items")
    await asyncio.sleep(0.2)  # Simulate processing
    return [f"Processed: {item}" for item in data]


@workflow_task(name="data_workflow")
async def data_workflow(input_data: List[str]) -> Dict[str, Any]:
    """A workflow task that orchestrates multiple steps."""
    print(f"Starting workflow with {len(input_data)} items")
    
    # First step
    processed_data = await process_data_step(input_data)
    
    # Second step - we could call another step here
    results = await asyncio.gather(*[async_llm_call(item) for item in processed_data])
    
    return {
        "input_count": len(input_data),
        "processed_count": len(processed_data),
        "results": results
    }


async def main():
    """Run the async examples."""
    # Start session
    session_info = await start_async_session()
    print(f"Session started: {session_info}")
    
    # Call agent
    agent_result = await async_agent("What is the capital of France?")
    print(f"Agent result: {agent_result}")
    
    # Run workflow
    workflow_result = await data_workflow(["item1", "item2", "item3"])
    print(f"Workflow result: {workflow_result}")


if __name__ == "__main__":
    asyncio.run(main()) 