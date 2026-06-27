"""
AgentOps Usage Examples

This file demonstrates the correct ways to use AgentOps for tracing and monitoring.
The error you encountered was due to trying to use agentops.trace() as a context manager,
when it's actually a decorator. Use agentops.start_trace() for context manager usage.
"""

import agentops
from agentops import start_trace, end_trace, trace

# 1. Initialize AgentOps
agentops.init(
    api_key="your_api_key_here",  # or set AGENTOPS_API_KEY environment variable
    trace_name="my_application",
    default_tags=["production", "v1.0"]
)

# 2. CORRECT: Using start_trace as a context manager
print("=== Context Manager Usage ===")
with start_trace("debug_test") as trace_context:
    print(f"Active trace: {trace_context}")
    print("This is the correct way to use AgentOps as a context manager")
    
    # Your application code here
    result = "some operation result"
    
    # The trace automatically ends when exiting the context
    # No need to manually call end_trace()

# 3. CORRECT: Manual trace management
print("\n=== Manual Trace Management ===")
trace_context = start_trace("manual_trace", tags=["manual", "example"])
try:
    print("Manual trace management example")
    # Your application code here
    result = "manual operation result"
finally:
    end_trace(trace_context, "Success")

# 4. CORRECT: Using @trace decorator for functions
print("\n=== Decorator Usage ===")
@trace("function_trace")
def my_function(param1, param2):
    print(f"Function called with {param1} and {param2}")
    return param1 + param2

# Call the decorated function
result = my_function(10, 20)
print(f"Function result: {result}")

# 5. CORRECT: Using @trace decorator with parameters
print("\n=== Decorator with Parameters ===")
@trace(name="complex_operation", tags=["complex", "calculation"])
def complex_calculation(x, y):
    print(f"Performing complex calculation with {x} and {y}")
    return x * y + 100

result = complex_calculation(5, 10)
print(f"Complex calculation result: {result}")

# 6. CORRECT: Nested traces
print("\n=== Nested Traces ===")
with start_trace("outer_trace") as outer:
    print("Outer trace started")
    
    with start_trace("inner_trace") as inner:
        print("Inner trace started")
        # Inner trace code
        print("Inner trace completed")
    
    print("Outer trace completed")

# 7. CORRECT: Async function with decorator
print("\n=== Async Function with Decorator ===")
import asyncio

@trace("async_operation")
async def async_operation():
    print("Async operation started")
    await asyncio.sleep(0.1)  # Simulate async work
    print("Async operation completed")
    return "async result"

# Run async function
async def main():
    result = await async_operation()
    print(f"Async result: {result}")

# Uncomment to run async example
# asyncio.run(main())

# 8. CORRECT: Error handling with traces
print("\n=== Error Handling ===")
try:
    with start_trace("error_handling_example") as trace:
        print("Starting operation that might fail")
        # Simulate an error
        raise ValueError("This is a test error")
except ValueError as e:
    print(f"Caught error: {e}")
    # The trace will automatically end with error state

# 9. CORRECT: Multiple concurrent traces
print("\n=== Multiple Concurrent Traces ===")
trace1 = start_trace("concurrent_trace_1", tags=["concurrent"])
trace2 = start_trace("concurrent_trace_2", tags=["concurrent"])

try:
    print("Working on trace 1")
    # Work for trace 1
    
    print("Working on trace 2")
    # Work for trace 2
    
finally:
    end_trace(trace1, "Success")
    end_trace(trace2, "Success")

print("\n=== All examples completed successfully! ===")

# 10. INCORRECT USAGE (what caused your error):
"""
# DON'T DO THIS - This will cause AttributeError:
with agentops.trace("debug_test"):
    print("This will fail!")

# The error occurs because agentops.trace() returns a decorator function,
# not a context manager. Decorator functions don't have __enter__ and __exit__ methods.
"""