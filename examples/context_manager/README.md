# AgentOps Context Manager Examples

This directory contains examples demonstrating how to use AgentOps with context managers for automatic trace lifecycle management using the simplified, native implementation.

## Overview

AgentOps provides native context manager support through the `TraceContext` class. This implementation eliminates wrapper classes and leverages OpenTelemetry's built-in capabilities for clean, automatic trace management.

## Key Benefits

- **Automatic cleanup**: Traces end automatically when exiting the context
- **Error handling**: Traces are marked with appropriate error states when exceptions occur
- **Native OpenTelemetry integration**: Leverages OpenTelemetry's built-in context management
- **Simplified architecture**: No wrapper classes or monkey patching required
- **Thread safety**: Works seamlessly in multi-threaded environments
- **Performance optimized**: Direct method calls without wrapper overhead

## Quick Start

```python
import agentops

# Initialize AgentOps
agentops.init(api_key="your-api-key")

# Use native context manager support
with agentops.start_trace("my_task") as trace:
    # Your code here
    pass  # Trace automatically ends with Success/Error state
```

## Examples

### `basic_usage.py`
- Native TraceContext context manager usage
- Multiple parallel traces
- Error handling basics
- Comparison with OpenTelemetry concepts

### `parallel_traces.py`
- Sequential and nested parallel traces
- Concurrent traces with threading and ThreadPoolExecutor
- Mixed success/error scenarios
- Different tag types (lists, dictionaries, none)

### `error_handling.py`
- Exception handling with different error types
- Nested exception handling and propagation
- Recovery patterns (retry, graceful degradation, partial success)
- Custom exceptions, finally blocks, and exception chaining

### `production_patterns.py`
- API endpoint monitoring and metrics
- Batch processing with individual item tracking
- Microservice communication patterns
- Production monitoring and alerting

## Running Examples

### Step 1: Install Dependencies

```bash
# Install required packages
pip install agentops python-dotenv
```

### Step 2: Set Up API Key

To use AgentOps and send trace data to your dashboard, you need to configure your API key using one of these methods:

**Option A: Environment Variable**
```bash
# Export directly in your shell
export AGENTOPS_API_KEY="your-api-key-here"
```

**Option B: .env File (Recommended)**
```bash
# Create a .env file in the project root
echo "AGENTOPS_API_KEY=your-api-key-here" > .env
```

**Important**: When using a `.env` file, the examples automatically load it using `load_dotenv()`. Make sure the `.env` file is in the same directory as the example scripts or in the project root.

### Step 3: Run the Examples

```bash
# Run each example to see different patterns
python examples/context_manager/basic_usage.py
python examples/context_manager/parallel_traces.py
python examples/context_manager/error_handling.py
python examples/context_manager/production_patterns.py
```
