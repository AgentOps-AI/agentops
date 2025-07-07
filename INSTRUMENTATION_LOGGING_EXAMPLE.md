# Instrumentation Logging Example

## Overview

This document demonstrates how the AgentOps SDK now displays instrumented libraries directly in the session URL log instead of through separate debug logs.

## Before (Old Behavior)

When libraries were instrumented, you would see multiple log messages:

```
AgentOps: Successfully instrumented 'OpenAIInstrumentor' for package 'openai'.
AgentOps: Successfully instrumented 'AnthropicInstrumentor' for package 'anthropic'.
AgentOps: Successfully instrumented 'LangChainInstrumentor' for package 'langchain'.
Session Replay for session trace: https://app.agentops.ai/sessions?trace_id=abc123def456
```

## After (New Behavior)

Now, instrumented libraries are shown in a single line with the session URL:

```
Session Replay for session trace: https://app.agentops.ai/sessions?trace_id=abc123def456 (instrumented: anthropic, langchain, openai)
```

## Benefits

1. **Cleaner Output**: Reduces console clutter by consolidating information
2. **Better Context**: Shows instrumented libraries right where the session URL is printed
3. **Easier Debugging**: You can immediately see which libraries are being tracked in your session

## Implementation Details

The changes include:
- Modified `log_trace_url()` to accept an optional `instrumented_libraries` parameter
- Added `get_instrumented_libraries()` function to retrieve the list of active instrumentations
- Changed instrumentation log levels from `info` to `debug` to reduce noise
- The instrumented libraries are only shown on the first session URL print (when starting a trace)

## Example Code

```python
import agentops

# Initialize AgentOps
agentops.init()

# Import libraries that will be instrumented
import openai
import anthropic

# When the session starts, you'll see:
# Session Replay for session trace: https://app.agentops.ai/sessions?trace_id=... (instrumented: anthropic, openai)

# Your code here...

agentops.end_session()
```