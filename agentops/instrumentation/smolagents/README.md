# SmoLAgents Instrumentation

This module provides OpenTelemetry instrumentation for the SmoLAgents framework. It captures telemetry data from model operations, agent executions, and tool usage.

## Features

- Model operation tracking
  - Text generation
  - Token usage
  - Streaming responses
  - Latency metrics

- Agent execution monitoring
  - Step-by-step execution
  - Planning phases
  - Tool usage
  - Execution time

- Tool usage analytics
  - Tool call patterns
  - Success/failure rates
  - Execution time
  - Error tracking

## Usage

```python
from agentops import init
from agentops.instrumentation.smolagents import SmoLAgentsInstrumentor

# Initialize AgentOps with your API key
init(api_key="your-api-key")

# The instrumentation will be automatically activated
# All SmoLAgents operations will now be tracked
```

## Metrics Collected

1. Token Usage
   - Input tokens
   - Output tokens
   - Total tokens per operation

2. Timing Metrics
   - Operation duration
   - Time to first token (streaming)
   - Tool execution time
   - Planning phase duration

3. Agent Metrics
   - Step counts
   - Planning steps
   - Tools used
   - Success/failure rates

4. Error Tracking
   - Generation errors
   - Tool execution errors
   - Parsing errors

## Architecture

The instrumentation is built on OpenTelemetry and follows the same pattern as other AgentOps instrumentors:

1. Attribute Extractors
   - Model attributes
   - Agent attributes
   - Tool call attributes

2. Wrappers
   - Method wrappers for sync operations
   - Stream wrappers for async operations
   - Context propagation handling

3. Metrics
   - Histograms for distributions
   - Counters for events
   - Custom attributes for filtering

## Contributing

When adding new features or modifying existing ones:

1. Follow the established pattern for attribute extraction
2. Maintain context propagation
3. Add appropriate error handling
4. Update tests and documentation 