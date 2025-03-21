# OpenAI Responses Instrumentation Examples

This directory contains examples demonstrating the instrumentation of both OpenAI API formats:
1. Traditional Chat Completions API
2. New Response API format (used by the Agents SDK)

## Dual API Example

The `dual_api_example.py` script shows both API formats in action with AgentOps instrumentation. It makes consecutive requests to:
1. The OpenAI Chat Completions API
2. The OpenAI Agents SDK (which uses the Response API format)

This demonstrates how our instrumentation correctly handles both formats and maintains proper trace context between them.

## Running the Example

```bash
# From the project root directory
AGENTOPS_LOG_LEVEL=debug uv run examples/openai_responses/dual_api_example.py
```

You'll need:
- An OpenAI API key set in your environment
- The OpenAI Python client installed
- The OpenAI Agents SDK installed

## What to Observe

In the AgentOps dashboard, you'll see:
- Both API formats correctly instrumented with appropriate spans
- Token usage metrics from both formats normalized to consistent attributes
- Content extraction from both formats mapped to semantic conventions
- All spans properly connected in the trace hierarchy