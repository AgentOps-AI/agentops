# AgentOps Instrumentation

This directory contains OpenTelemetry-based instrumentation for various LLM providers, agent frameworks, and utilities.

## Directory Structure

```
instrumentation/
├── common/                      # Shared modules for all instrumentors
│   ├── base_instrumentor.py    # Base class with common functionality
│   ├── config.py               # Shared configuration
│   ├── streaming.py            # Base streaming wrapper
│   ├── metrics.py              # Metrics management
│   ├── wrappers.py             # Method wrapping utilities
│   └── attributes.py           # Common attribute extractors
│
├── providers/                   # LLM Provider Instrumentors
│   ├── openai/                 # OpenAI API
│   ├── anthropic/              # Anthropic Claude
│   ├── google_genai/           # Google Generative AI
│   └── ibm_watsonx_ai/         # IBM watsonx.ai
│
├── frameworks/                  # Agent Framework Instrumentors
│   ├── ag2/                    # AG2 (AutoGen)
│   ├── agno/                   # Agno
│   ├── crewai/                 # CrewAI
│   ├── openai_agents/          # OpenAI Agents SDK
│   └── smolagents/             # SmoLAgents
│
└── utilities/                   # Utility Instrumentors
    └── concurrent_futures/      # Thread pool context propagation
```

## Quick Start

### Using an Instrumentor

```python
from agentops import AgentOps

# Initialize AgentOps with automatic instrumentation
agentops = AgentOps(api_key="your-api-key")

# Or manually instrument specific libraries
from agentops.instrumentation.providers.openai import OpenAIInstrumentor

instrumentor = OpenAIInstrumentor()
instrumentor.instrument()
```

### Common Module Usage

All instrumentors inherit from `AgentOpsBaseInstrumentor` which provides:

- Automatic tracer and meter initialization
- Standard metric creation
- Method wrapping/unwrapping infrastructure
- Error handling and logging

Example implementation:

```python
from agentops.instrumentation.common.base_instrumentor import AgentOpsBaseInstrumentor
from agentops.instrumentation.common.wrappers import WrapConfig

class MyInstrumentor(AgentOpsBaseInstrumentor):
    def instrumentation_dependencies(self):
        return ["my-package >= 1.0.0"]
    
    def _init_wrapped_methods(self):
        return [
            WrapConfig(
                trace_name="my_service.operation",
                package="my_package.module",
                class_name="MyClass",
                method_name="my_method",
                handler=self._get_attributes,
            ),
        ]
    
    def _get_attributes(self, args, kwargs, return_value=None):
        """Extract attributes from method arguments and return value."""
        return {
            "my.attribute": kwargs.get("param", "default"),
            # Add more attributes as needed
        }
```

### Streaming Support

For providers with streaming responses, use the common `StreamingResponseWrapper`:

```python
from agentops.instrumentation.common.streaming import StreamingResponseWrapper

class MyStreamWrapper(StreamingResponseWrapper):
    def _process_chunk(self, chunk):
        """Process individual streaming chunks."""
        # Extract content from chunk
        content = chunk.get("content", "")
        
        # Accumulate for span attributes
        self._accumulated_content.append(content)
        
        # Return processed chunk
        return chunk
```

### Metrics

Common metrics are automatically initialized:

- `llm.operation.duration` - Operation duration histogram
- `llm.token.usage` - Token usage histogram
- `llm.completions.exceptions` - Exception counter

Access metrics through the `MetricsManager`:

```python
from agentops.instrumentation.common.metrics import MetricsManager

# In your instrumentor
metrics = MetricsManager.init_metrics(meter, prefix="my_provider")
```

## Module Categories

### Providers

LLM API provider instrumentors capture:
- Model parameters (temperature, max_tokens, etc.)
- Request/response content
- Token usage
- Streaming responses
- Tool/function calls

### Frameworks

Agent framework instrumentors capture:
- Agent initialization and configuration
- Agent-to-agent communication
- Tool usage
- Workflow execution
- Team/crew coordination

### Utilities

Infrastructure instrumentors provide:
- Context propagation across threads
- Performance monitoring
- System resource tracking

## Best Practices

1. **Use the Common Base Class**: Inherit from `AgentOpsBaseInstrumentor` for consistency
2. **Separate Attribute Logic**: Keep attribute extraction in separate functions or modules
3. **Handle Errors Gracefully**: Always fall back to original behavior on errors
4. **Log Appropriately**: Use debug logging for instrumentation details
5. **Test Thoroughly**: Include unit tests for all wrapped methods

## Adding New Instrumentors

See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines on adding new instrumentors.

## Semantic Conventions

All instrumentors follow OpenTelemetry semantic conventions. See [agentops/semconv](../semconv/README.md) for available attributes.

## Troubleshooting

### Debug Logging

Enable debug logging to see instrumentation details:

```python
import logging
logging.getLogger("agentops").setLevel(logging.DEBUG)
```

### Common Issues

1. **Import Errors**: Ensure the target library is installed
2. **Method Not Found**: Check if the method signature has changed
3. **Context Loss**: For async/threading, ensure proper context propagation

## License

See individual module directories for specific license information.
