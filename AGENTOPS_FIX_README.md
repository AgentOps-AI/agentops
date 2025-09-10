# AgentOps Usage Fix

## The Problem

You encountered this error:
```
AttributeError: 'str' object has no attribute '__enter__'. Did you mean: '__iter__'?
```

This error occurs when you try to use `agentops.trace()` as a context manager:

```python
# ❌ INCORRECT - This causes the error
with agentops.trace("debug_test"):
    print("This will fail!")
```

## The Root Cause

The issue is that `agentops.trace()` is a **decorator**, not a context manager. Decorators are used to wrap functions, not to create context managers.

## The Solution

Use `agentops.start_trace()` for context manager usage:

```python
# ✅ CORRECT - Use start_trace for context manager
with agentops.start_trace("debug_test") as trace:
    print("This works correctly!")
    # Your code here
    # Trace automatically ends when exiting the context
```

## Complete Usage Guide

### 1. Context Manager Usage (for code blocks)
```python
import agentops

# Initialize AgentOps
agentops.init()

# Use as context manager
with agentops.start_trace("my_operation") as trace:
    print("Working on my operation")
    result = perform_some_work()
    # Trace automatically ends here
```

### 2. Decorator Usage (for functions)
```python
import agentops
from agentops import trace

@trace("my_function")
def my_function():
    print("This function is being traced")
    return "result"

# Call the function
result = my_function()
```

### 3. Manual Trace Management
```python
import agentops
from agentops import start_trace, end_trace

# Start trace manually
trace_context = start_trace("manual_trace")

try:
    print("Working on manual trace")
    # Your code here
finally:
    # End trace manually
    end_trace(trace_context, "Success")
```

### 4. With Tags and Parameters
```python
# Context manager with tags
with agentops.start_trace("tagged_trace", tags=["production", "v1.0"]) as trace:
    print("Working with tags")

# Decorator with parameters
@agentops.trace(name="complex_operation", tags=["complex", "calculation"])
def complex_function():
    return "complex result"
```

## Key Differences

| Usage | Function | Purpose | Example |
|-------|----------|---------|---------|
| Context Manager | `agentops.start_trace()` | Wrap code blocks | `with start_trace("name"):` |
| Decorator | `agentops.trace()` | Wrap functions | `@trace("name")` |

## Common Patterns

### Nested Traces
```python
with agentops.start_trace("outer") as outer:
    with agentops.start_trace("inner") as inner:
        print("Nested tracing")
```

### Error Handling
```python
try:
    with agentops.start_trace("error_example") as trace:
        # This might fail
        raise ValueError("Test error")
except ValueError:
    # Trace automatically ends with error state
    pass
```

### Multiple Concurrent Traces
```python
trace1 = agentops.start_trace("trace1")
trace2 = agentops.start_trace("trace2")

try:
    # Work on both traces
    pass
finally:
    agentops.end_trace(trace1)
    agentops.end_trace(trace2)
```

## Files in This Repository

- `main.py` - Basic example showing correct usage
- `agentops_usage_examples.py` - Comprehensive examples of all usage patterns
- `AGENTOPS_FIX_README.md` - This documentation

## Quick Fix for Your Code

Replace this:
```python
with agentops.trace("debug_test"):
    # your code
```

With this:
```python
with agentops.start_trace("debug_test") as trace:
    # your code
```

That's it! The trace will automatically end when you exit the context block.