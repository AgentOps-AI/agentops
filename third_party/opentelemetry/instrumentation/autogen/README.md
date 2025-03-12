# AutoGen Instrumentation for AgentOps

This package provides OpenTelemetry instrumentation for [AutoGen](https://github.com/microsoft/autogen), enabling detailed tracing and metrics collection for AutoGen agents and their interactions.

## Features

- Traces agent initialization and configuration
- Captures message exchanges between agents
- Monitors LLM API calls and token usage
- Tracks tool/function execution
- Observes group chat interactions
- Collects performance metrics

## Installation

The instrumentation is included as part of the AgentOps package. No separate installation is required.

## Usage

### Basic Usage

```python
import agentops
from opentelemetry.instrumentation.autogen import AutoGenInstrumentor
import autogen

# Initialize AgentOps
agentops.init(api_key="your-api-key")

# Start a session
session = agentops.start_session()

# Instrument AutoGen
instrumentor = AutoGenInstrumentor()
instrumentor.instrument()

# Create and use AutoGen agents as usual
assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={"model": "gpt-4"}
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    code_execution_config={"use_docker": False}
)

# Start a conversation
user_proxy.initiate_chat(
    assistant,
    message="Hello, can you help me solve a math problem?"
)

# End the session when done
agentops.end_session("success")
```

### Uninstrumenting

To remove the instrumentation:

```python
instrumentor.uninstrument()
```

## Captured Spans

The instrumentation captures the following key spans:

- `autogen.agent.generate_reply`: Message generation - high-level view of message exchanges
- `autogen.agent.generate_oai_reply`: LLM API calls - captures token usage and model information
- `autogen.agent.execute_function`: Tool/function execution - tracks tool usage
- `autogen.team.groupchat.run`: Group chat execution - for multi-agent scenarios

These spans were carefully selected to provide comprehensive tracing while minimizing overhead. We've removed redundant spans that were generating excessive telemetry data.

## Metrics

The instrumentation collects the following metrics:

- `autogen.llm.token_usage`: Token usage for LLM calls
- `autogen.operation.duration`: Duration of various operations

## Attributes

Each span includes relevant attributes such as:

### For `autogen.agent.generate_reply`:
- Agent name, description, and sender
- System message content
- Input messages (content, source, type)
- Agent state information (message count, tool count)
- Message content and count
- LLM model and configuration (temperature, max_tokens, etc.)
- Token usage (total, prompt, and completion tokens) - extracted using multiple approaches
- Function call information (name, arguments)
- Estimated token counts when actual counts aren't available
- Token usage availability flag (`llm.token_usage.found`)

### For `autogen.agent.generate_oai_reply`:
- Agent name and description
- System message content
- LLM model and provider
- Detailed configuration (temperature, max_tokens, top_p, etc.)
- Input messages (role, content, function calls)
- Input message count and estimated token count
- Model context information (buffer size)
- Tools information (count, names)
- Output content and estimated token count
- Response finish reason
- Actual token usage (total, prompt, and completion tokens) - extracted using multiple approaches
- Estimated cost in USD (for OpenAI models)
- Function call information (name, arguments)
- Token usage availability flag (`llm.token_usage.found`)

### For `autogen.agent.execute_function`:
- Agent name
- Tool name and arguments
- Execution result and duration

### For `autogen.team.groupchat.run`:
- Team name
- Number of agents in the group
- Execution duration

## Debugging Token Usage

If token information isn't appearing in your spans, you can check the `llm.token_usage.found` attribute in spans to see if token usage was found. The instrumentation attempts multiple approaches to extract token usage information, adapting to different AutoGen versions and response structures.

## Example

See the `autogentest.py` file for a comprehensive example of using the instrumentation with different AutoGen features.

## Compatibility

This instrumentation is compatible with AutoGen versions 0.2.x and later.

## License

This instrumentation is part of the AgentOps package and is subject to the same license terms. 