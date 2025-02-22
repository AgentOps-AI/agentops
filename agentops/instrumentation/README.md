# AgentOps Instrumentation

This package provides OpenTelemetry instrumentation for various LLM providers and related services.

## Available Instrumentors

- OpenAI (`v0.27.0+` and `v1.0.0+`)


## Usage

### OpenAI Instrumentation

```python
from agentops.instrumentation.openai import OpenAIInstrumentor

from agentops.telemetry.session import get_tracer_provider()

# Initialize and instrument
instrumentor = OpenAIInstrumentor(
    enrich_assistant=True,  # Include assistant messages in spans
    enrich_token_usage=True,  # Include token usage in spans
    enable_trace_context_propagation=True,  # Enable trace context propagation
)
instrumentor.instrument(tracer_provider=tracer_provider) # <-- Uses the global AgentOps TracerProvider 
```
