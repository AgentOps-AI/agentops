# AgentOps Examples Integration Testing

This directory contains example scripts demonstrating how to use AgentOps with various LLM providers and frameworks. Each example includes automatic validation to ensure that LLM spans are properly tracked by AgentOps.

## What's Being Tested

Each example script now includes automated span validation that:

1. **Runs the example** - Executes the normal example code
2. **Validates span tracking** - Uses the AgentOps integrated validation to verify that:
   - Spans were successfully sent to AgentOps
   - LLM calls were properly instrumented and tracked
   - Token counts and costs were recorded

## How It Works

### 1. Integrated Validation

AgentOps now includes built-in validation functionality (`agentops.validate_trace_spans`) that:
- Exchanges API keys for JWT tokens using the public API
- Queries the AgentOps API for trace and span data
- Validates that expected spans are present
- Retrieves metrics like token usage and costs

### 2. Example Structure

Each example follows this pattern:

```python
import agentops

# Initialize AgentOps
agentops.init()

# Start a trace
tracer = agentops.start_trace("example-name")

# ... perform operations with LLMs ...

# End the trace
agentops.end_trace(tracer, end_state="Success")

# Validate spans were tracked
try:
    result = agentops.validate_trace_spans(trace_context=tracer)
    agentops.print_validation_summary(result)
except agentops.ValidationError as e:
    print(f"❌ Error validating spans: {e}")
    raise
```

### 3. CI/CD Integration

The GitHub Actions workflow (`examples-integration-test.yml`) runs all examples automatically on:
- Push to main/develop branches
- Pull requests
- Manual workflow dispatch

Each example is run in isolation with proper error handling and reporting.

## Running Tests Locally

To run a specific example with validation:

```bash
cd examples/openai
python openai_example_sync.py
```

To run all examples:

```bash
# From the examples directory
for script in $(find . -name "*.py" -type f | grep -v "__pycache__"); do
    echo "Running $script..."
    python "$script"
done
```

## Adding New Examples

When adding a new example:

1. Include the standard validation at the end:
   ```python
   # Validate spans were tracked
   try:
       result = agentops.validate_trace_spans(trace_context=tracer)
       agentops.print_validation_summary(result)
   except agentops.ValidationError as e:
       print(f"❌ Error validating spans: {e}")
       raise
   ```

2. Add the example to the GitHub Actions matrix in `.github/workflows/examples-integration-test.yml`

3. Ensure the example has proper error handling

## Requirements

- Valid `AGENTOPS_API_KEY` environment variable
- API keys for the specific LLM provider being tested
- Python 3.12+ with required dependencies 