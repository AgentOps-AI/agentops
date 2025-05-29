# AgentOps Context Manager Examples

This directory contains comprehensive examples demonstrating the new context manager functionality for AgentOps. Each example focuses on a specific use case or pattern and is completely standalone.

## 📁 Example Files

### Core Examples
- **`01_basic_usage.py`** - Simple context manager usage and comparison with traditional approach
- **`02_exception_handling.py`** - How exceptions are handled and traces are cleaned up automatically
- **`03_backward_compatibility.py`** - Demonstrates that existing code continues to work unchanged
- **`04_retry_logic.py`** - Implementing retry patterns with individual traces per attempt

## 🚀 Quick Start

1. **Set your API key:**
   ```bash
   export AGENTOPS_API_KEY="your-api-key-here"
   ```
   Or create a `.env` file with:
   ```
   AGENTOPS_API_KEY=your-api-key-here
   ```

2. **Run any example:**
   ```bash
   python examples/context_manager/01_basic_usage.py
   python examples/context_manager/02_exception_handling.py
   python examples/context_manager/03_backward_compatibility.py
   python examples/context_manager/04_retry_logic.py
   ```

## 🎯 Key Benefits Demonstrated

- **Automatic Lifecycle Management**: Traces are automatically started and ended
- **Exception Safety**: Guaranteed cleanup even when errors occur
- **Clear Scope Definition**: Easy to see what operations belong to which trace
- **Backward Compatibility**: Existing code continues to work unchanged
- **Flexible Patterns**: Supports retry logic, error recovery, and complex workflows

## 📖 Learning Path

1. **Start with `01_basic_usage.py`** to understand the fundamentals
   - Compare traditional vs context manager approaches
   - See automatic session lifecycle management
   - Learn basic patterns

2. **Review `02_exception_handling.py`** to see error handling
   - Understand how exceptions are handled
   - See guaranteed cleanup behavior
   - Learn error state recording

3. **Check `03_backward_compatibility.py`** for migration confidence
   - See that existing code works unchanged
   - Learn about mixed usage patterns
   - Understand migration strategies

4. **Explore `04_retry_logic.py`** for advanced patterns
   - Implement retry logic with individual traces
   - Handle different error types
   - Use exponential backoff and conditional retries

## 💡 Example Features

- **All examples are completely standalone** - no shared dependencies
- Each example includes its own agent class definition
- Examples use environment variables for API keys
- All examples include detailed comments explaining the patterns
- Check the console output to see trace lifecycle events
- Each example demonstrates different aspects of the context manager

## 🔧 Context Manager Benefits

### Traditional Approach
```python
session = agentops.init(api_key=API_KEY, auto_start_session=True)
# ... do work ...
agentops.end_session()  # Must remember to call this!
```

### Context Manager Approach
```python
with agentops.init(api_key=API_KEY, trace_name="my_trace") as session:
    # ... do work ...
    # Session automatically ended, even if exceptions occur!
```

## 🛡️ Error Handling

The context manager guarantees:
- **Traces are ALWAYS cleaned up**, even with exceptions
- **Exceptions are NEVER suppressed**
- **Error state is properly recorded** for debugging
- **All data recorded before errors is preserved**

## 🔄 Migration Strategy

You can adopt context managers gradually:
- **No breaking changes** - existing code continues to work
- **Mix old and new patterns** as needed
- **Adopt incrementally** - no pressure to refactor everything at once
- **Get automatic cleanup benefits** immediately for new code
