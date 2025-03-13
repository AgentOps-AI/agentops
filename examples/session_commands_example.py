"""
Example demonstrating how to use the AgentOps session commands.

This example shows three different ways to manage session spans:
1. Using the start_session and end_session functions directly
2. Using the session_context context manager
3. Using the @session decorator

Run this example with:
    uv run examples/session_commands_example.py
"""

import time

import agentops
from agentops.sdk._facade import session_context
from agentops.sdk.commands import end_session, record, start_session
from agentops.sdk.decorators import operation

# Initialize AgentOps with your API key
# In a real application, you would use your actual API key
agentops.init()


def example_1_manual_session():
    """Example using start_session and end_session functions directly."""
    print("Example 1: Manual session control")

    # Start a session manually
    span, token = start_session(
        name="manual_session",
        attributes={"example": "manual", "method": "direct_functions"}
    )

    # Simulate some work
    record("This will generate a span within the 'manual_session' session")

    # End the session manually
    end_session(span, token)
    print("  Manual session ended")




if __name__ == "__main__":
    # Run all examples
    example_1_manual_session()
