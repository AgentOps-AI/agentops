# AgentOps Instrumentation

This package provides OpenTelemetry instrumentation for various LLM providers and related services.

## Available Instrumentors

- OpenAI (`v0.27.0+` and `v1.0.0+`)


## Usage

### OpenAI Instrumentation

```python
from opentelemetry import trace
from opentelemetry.trace import TracerProvider
from agentops.instrumentation.openai import OpenAIInstrumentor

# Set up the tracer provider
tracer_provider = TracerProvider()

# Initialize and instrument
instrumentor = OpenAIInstrumentor(
    enrich_assistant=True,  # Include assistant messages in spans
    enrich_token_usage=True,  # Include token usage in spans
    enable_trace_context_propagation=True,  # Enable trace context propagation
)
instrumentor.instrument(tracer_provider=tracer_provider)
```

#### Configuration Options

- `enrich_assistant` (bool): Include assistant messages in spans
- `enrich_token_usage` (bool): Include token usage metrics in spans
- `exception_logger` (Callable): Custom exception logger
- `get_common_metrics_attributes` (Callable): Function to get common attributes for metrics
- `upload_base64_image` (Callable): Function to handle base64 image uploads
- `enable_trace_context_propagation` (bool): Enable trace context propagation across requests

### Uninstrumenting

To remove instrumentation:

```python
instrumentor.uninstrument()
```

## Custom Metrics and Attributes

You can provide custom metrics attributes through the `get_common_metrics_attributes` parameter:

```python
def get_metrics_attributes():
    return {
        "environment": "production",
        "service.name": "my-llm-service"
    }

instrumentor = OpenAIInstrumentor(
    get_common_metrics_attributes=get_metrics_attributes
)
```

## Session Context

The instrumentor automatically includes session information in metrics when using AgentOps sessions:

- `session.id`: Current session ID
- `session.state`: Current session state

## Trace Context Propagation

When `enable_trace_context_propagation` is enabled, the instrumentor will:
1. Extract trace context from incoming requests
2. Inject trace context into outgoing requests
3. Maintain trace context across async operations

This ensures distributed tracing works correctly across your entire system.
```

This README provides a clear overview of how to use the instrumentation, focusing on the OpenAI instrumentor since that's currently implemented. As more providers are added, the README can be expanded to include their specific configuration options and usage patterns.
