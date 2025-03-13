"""
Example demonstrating how to use the AgentOps session commands.

This example shows three different ways to manage session spans:
1. Using the start_session and end_session functions directly

Run this example with:
    uv run examples/session_commands_example.py
"""

import time

import agentops
from agentops.sdk.commands import end_span, record, start_span
from agentops.sdk.decorators import operation
from agentops.semconv.span_kinds import SpanKind

# Initialize AgentOps with your API key
# In a real application, you would use your actual API key
agentops.init()


def example_1_manual_session():
    """Example using start_session and end_session functions directly."""
    print("Example 1: Manual session control")

    # Start a session manually
    span, token = start_span(
        name="manual_session",
        span_kind=SpanKind.SESSION,
        attributes={"example": "manual", "method": "direct_functions"}
    )

    # Simulate some work
    record("This will generate a span within the 'manual_session' session")

    # End the session manually
    end_span(span, token)
    print("  Manual session ended")




if __name__ == "__main__":
    # Run all examples
    example_1_manual_session()
