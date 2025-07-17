# OpenAI o3 Responses API Integration Test

This directory contains integration tests for AgentOps with OpenAI's o3 reasoning model using the Responses API.

## Overview

The o3 model is OpenAI's reasoning model that excels at complex problem solving and multi-step reasoning. This integration test demonstrates how AgentOps can track and monitor o3 model calls that use the Responses API with tool calls.

## Files

- `o3_responses_integration_test.py` - Full integration test with multiple scenarios
- `test_o3_integration.py` - Simple test script for quick verification
- `README_o3_integration.md` - This file

## Prerequisites

1. **OpenAI API Key**: You need access to the o3 model through OpenAI's API
2. **AgentOps API Key**: Required for tracing and monitoring
3. **Python Dependencies**: Install the required packages

```bash
pip install openai agentops python-dotenv
```

## Environment Setup

Create a `.env` file in the `examples/openai/` directory with your API keys:

```env
OPENAI_API_KEY=your_openai_api_key_here
AGENTOPS_API_KEY=your_agentops_api_key_here
```

## Running the Tests

### Simple Test

For a quick verification that the integration works:

```bash
cd examples/openai
python test_o3_integration.py
```

This test:
- Makes a single o3 API call with tool calls
- Verifies that AgentOps captures the interaction
- Validates the trace spans

### Full Integration Test

For a comprehensive test with multiple scenarios:

```bash
cd examples/openai
python o3_responses_integration_test.py
```

This test:
- Runs multiple decision-making scenarios
- Demonstrates complex reasoning with tool calls
- Shows how AgentOps tracks the full interaction flow
- Validates trace spans and provides detailed output

## What the Tests Demonstrate

1. **o3 Model Integration**: Using OpenAI's o3 model with the Responses API
2. **Tool Calls**: Proper handling of function calls and tool selection
3. **Reasoning Capture**: Capturing both the reasoning text and tool call arguments
4. **AgentOps Tracing**: Complete trace of the interaction with proper span validation
5. **Error Handling**: Graceful handling of missing tool calls or API errors

## Expected Output

The tests should show:
- Colored output indicating the o3 model's reasoning process
- Tool call selection with arguments
- AgentOps trace validation results
- Success/failure indicators

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure your OpenAI API key has access to the o3 model
2. **Missing Dependencies**: Install all required packages
3. **Environment Variables**: Check that your `.env` file is properly configured
4. **Network Issues**: Ensure you have internet access for API calls

### Debug Mode

To see more detailed output, you can modify the scripts to include debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with Your Code

To integrate this pattern into your own code:

1. Initialize AgentOps with appropriate tags
2. Use the `@agent` decorator on functions that make o3 calls
3. Structure your prompts to work with tool calls
4. Handle the Responses API output format properly
5. Validate traces to ensure proper monitoring

## Example Usage Pattern

```python
import agentops
from agentops.sdk.decorators import agent
import openai

# Initialize
agentops.init(trace_name="your-trace", tags=["o3", "your-tags"])
client = openai.OpenAI()

@agent
def your_o3_function():
    # Define tools
    tools = [...]
    
    # Make API call
    response = client.responses.create(
        model="o3",
        input=[...],
        tools=tools,
        tool_choice="required"
    )
    
    # Process response
    # Handle tool calls and reasoning
```

## Notes

- The o3 model requires specific access permissions from OpenAI
- The Responses API format is different from the standard Chat Completions API
- Tool calls in o3 provide both reasoning and structured output
- AgentOps captures the full interaction including reasoning and tool selection