# AgentOps Trace Usage Guide

## The Error

The user encountered this error:
```python
Traceback (most recent call last):
  File "/Users/amirjaveed/PycharmProjects/CrewAiAgentOpsPythonProject/main.py", line 28, in <module>
    with agentops.trace("debug_test"):
AttributeError: 'str' object has no attribute '__enter__'. Did you mean: '__iter__'?
```

## Root Cause

The error occurred because `agentops.trace` is a **decorator**, not a function that returns a context manager. When you call `agentops.trace("debug_test")`, it returns a decorator function (or a string in some cases), which cannot be used with the `with` statement.

## Solution

AgentOps provides two different ways to create traces:

### 1. `agentops.start_trace()` - For Context Manager Usage

Use `start_trace()` when you want to use a context manager (with statement):

```python
import agentops

# Initialize AgentOps
agentops.init(api_key="your_api_key", auto_start_session=False)

# Use as a context manager
with agentops.start_trace("debug_test") as trace_context:
    print("Inside trace context")
    # Your code here
    # The trace automatically ends when exiting the context
```

### 2. `@agentops.trace` - For Decorator Usage

Use `@trace` as a decorator for functions or classes:

```python
import agentops

# Initialize AgentOps
agentops.init(api_key="your_api_key", auto_start_session=False)

# Use as a decorator
@agentops.trace
def my_function():
    print("Inside traced function")
    return "result"

# Or with parameters
@agentops.trace(name="custom_name", tags={"type": "demo"})
def another_function(x, y):
    return x + y
```

## Key Differences

| Feature | `start_trace()` | `@trace` decorator |
|---------|----------------|-------------------|
| **Usage** | Context manager or manual | Function/class decorator |
| **Syntax** | `with start_trace():` | `@trace` above function |
| **Returns** | TraceContext object | Decorated function |
| **Scope** | Explicit block of code | Entire function execution |
| **Best for** | Dynamic tracing, conditional traces | Function-level instrumentation |

## Complete Working Examples

### Example 1: Context Manager (Recommended for your use case)
```python
import agentops

agentops.init(api_key="your_api_key", auto_start_session=False)

# This is what you wanted to do - use as a context manager
with agentops.start_trace("debug_test") as trace_context:
    print("Performing operations...")
    # Your code here
```

### Example 2: Manual Trace Management
```python
import agentops

agentops.init(api_key="your_api_key", auto_start_session=False)

# Start trace manually
trace_context = agentops.start_trace("manual_test")
try:
    # Your code here
    print("Performing operations...")
finally:
    # End trace manually
    agentops.end_trace(trace_context, end_state=agentops.SUCCESS)
```

### Example 3: Decorator on Functions
```python
import agentops

agentops.init(api_key="your_api_key", auto_start_session=False)

@agentops.trace
def process_data(data):
    # This entire function is traced
    return data.upper()

# Call the function normally
result = process_data("hello")
```

### Example 4: Decorator on Classes
```python
import agentops

agentops.init(api_key="your_api_key", auto_start_session=False)

@agentops.trace(name="DataProcessor")
class DataProcessor:
    def __init__(self, config):
        self.config = config
    
    def process(self, data):
        return data

# The class initialization is traced
processor = DataProcessor({"setting": "value"})
```

## Common Pitfalls to Avoid

1. **Don't use `trace()` as a function call for context managers**
   ```python
   # ❌ WRONG - This causes the AttributeError
   with agentops.trace("test"):
       pass
   
   # ✅ CORRECT - Use start_trace() instead
   with agentops.start_trace("test"):
       pass
   ```

2. **Don't forget to initialize AgentOps first**
   ```python
   # Always initialize before using traces
   agentops.init(api_key="your_key", auto_start_session=False)
   ```

3. **Don't mix up the import**
   - The `trace` from `agentops` is a decorator
   - If you see examples using `with trace():`, they might be using a different library's trace function (e.g., from `openai-agents`)

## Summary

- Use `agentops.start_trace()` when you need a context manager (with statement)
- Use `@agentops.trace` when you want to decorate functions or classes
- Both methods achieve similar results but are suited for different use cases
- The error you encountered was trying to use a decorator as a context manager

The corrected version of your code should be:
```python
import agentops

agentops.init(api_key="your_api_key", auto_start_session=False)

# Replace this:
# with agentops.trace("debug_test"):  # ❌ WRONG

# With this:
with agentops.start_trace("debug_test"):  # ✅ CORRECT
    # Your code here
    pass
```