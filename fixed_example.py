#!/usr/bin/env python3
"""
Corrected example showing proper AgentOps trace usage.

The error occurred because agentops.trace is a decorator, not a function that returns a context manager.
To use trace as a context manager, you should use agentops.start_trace() instead.
"""

import agentops
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize AgentOps with your API key
agentops.init(
    api_key=os.getenv("AGENTOPS_API_KEY", "f700a1...7b69"),  # Replace with your actual key
    auto_start_session=False  # Don't auto-start a session
)

# Method 1: Using start_trace() as a context manager (RECOMMENDED for context manager usage)
print("\n=== Method 1: Using start_trace() as a context manager ===")
with agentops.start_trace("debug_test") as trace_context:
    print(f"Inside trace context: {trace_context}")
    print("Performing some operations...")
    # Your code here
    print("Operations completed!")

# Method 2: Using start_trace() and end_trace() manually
print("\n=== Method 2: Manual trace management ===")
trace_context = agentops.start_trace("manual_test")
try:
    print("Performing operations in manual trace...")
    # Your code here
    print("Manual operations completed!")
finally:
    agentops.end_trace(trace_context, end_state=agentops.SUCCESS)

# Method 3: Using @trace decorator on functions (for function-level tracing)
print("\n=== Method 3: Using @trace decorator ===")
@agentops.trace
def my_function():
    print("Inside traced function")
    return "Function result"

result = my_function()
print(f"Function returned: {result}")

# Method 4: Using @trace decorator with parameters
print("\n=== Method 4: Using @trace decorator with parameters ===")
@agentops.trace(name="custom_trace_name", tags={"type": "demo"})
def another_function(x, y):
    print(f"Processing {x} and {y}")
    return x + y

result = another_function(5, 3)
print(f"Result: {result}")

print("\n=== All examples completed successfully! ===")