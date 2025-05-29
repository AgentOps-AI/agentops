"""
Basic Context Manager Example

This example demonstrates how to use AgentOps context manager with the native
TraceContext support, eliminating the need for wrappers or monkey patching.
"""

import os
import agentops
from agentops import agent, task, tool
from dotenv import load_dotenv

load_dotenv()

# Get API key from environment
AGENTOPS_API_KEY = os.environ.get("AGENTOPS_API_KEY")


@agent
class SimpleAgent:
    """A simple example agent."""

    def __init__(self, name: str):
        self.name = name

    @task
    def process_data(self, data: str) -> str:
        """Process some data."""
        result = f"Processed: {data}"
        return self.use_tool(result)

    @tool
    def use_tool(self, input_data: str) -> str:
        """Use a tool to transform data."""
        return f"Tool output: {input_data.upper()}"


def basic_context_manager_example():
    """Example using the native TraceContext context manager."""
    print("Basic Context Manager Example")

    # Initialize AgentOps
    agentops.init(api_key=AGENTOPS_API_KEY)

    # Use native TraceContext context manager
    with agentops.start_trace("basic_example", tags=["basic", "demo"]):
        print("Trace started")

        # Create and use agent
        agent = SimpleAgent("BasicAgent")
        result = agent.process_data("sample data")
        print(f"Result: {result}")

    print("Trace ended automatically")


def multiple_parallel_traces():
    """Example showing multiple parallel traces."""
    print("\nMultiple Parallel Traces")

    agentops.init(api_key=AGENTOPS_API_KEY)

    # First trace
    with agentops.start_trace("task_1", tags=["parallel", "task-1"]):
        print("Task 1 started")
        agent1 = SimpleAgent("Agent1")
        result1 = agent1.process_data("task 1 data")
        print(f"Task 1 result: {result1}")

    # Second trace (independent)
    with agentops.start_trace("task_2", tags=["parallel", "task-2"]):
        print("Task 2 started")
        agent2 = SimpleAgent("Agent2")
        result2 = agent2.process_data("task 2 data")
        print(f"Task 2 result: {result2}")

    print("All parallel traces completed")


def error_handling_example():
    """Example showing error handling with context manager."""
    print("\nError Handling Example")

    agentops.init(api_key=AGENTOPS_API_KEY)

    try:
        with agentops.start_trace("error_example", tags=["error-handling"]):
            print("Trace started")

            agent = SimpleAgent("ErrorAgent")
            result = agent.process_data("some data")
            print(f"Processing successful: {result}")

            # Simulate an error
            raise ValueError("Simulated error")

    except ValueError as e:
        print(f"Caught error: {e}")
        print("Trace automatically ended with Error status")


def nested_traces_example():
    """Example showing nested traces (which are parallel, not parent-child)."""
    print("\nNested Traces Example")

    agentops.init(api_key=AGENTOPS_API_KEY)

    # Outer trace
    with agentops.start_trace("main_workflow", tags=["workflow", "main"]):
        print("Main workflow started")

        # Inner trace (parallel, not child)
        with agentops.start_trace("sub_task", tags=["workflow", "sub"]):
            print("Sub task started")

            agent = SimpleAgent("WorkflowAgent")
            result = agent.process_data("workflow data")
            print(f"Sub task result: {result}")

        print("Sub task completed")
        print("Main workflow completed")


if __name__ == "__main__":
    print("AgentOps Context Manager Examples")
    print("=" * 40)

    # Show basic usage
    basic_context_manager_example()

    # Show multiple parallel traces
    multiple_parallel_traces()

    # Show error handling
    error_handling_example()

    # Show nested traces
    nested_traces_example()

    print("\nAll examples completed!")
