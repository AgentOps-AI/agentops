# AgentOps Instrumentation

This package provides OpenTelemetry instrumentation for various LLM providers and related services.

## Available Instrumentors

- OpenAI (`v0.27.0+` and `v1.0.0+`)


## Usage

### OpenAI Instrumentation

```python
from opentelemetry.instrumentation.openai import OpenAIInstrumentor

from agentops.telemetry import get_tracer_provider()

# Initialize and instrument
instrumentor = OpenAIInstrumentor(
    enrich_assistant=True,  # Include assistant messages in spans
    enrich_token_usage=True,  # Include token usage in spans
    enable_trace_context_propagation=True,  # Enable trace context propagation
)
instrumentor.instrument(tracer_provider=tracer_provider) # <-- Uses the global AgentOps TracerProvider
```

## Dependency Handling

OpenTelemetry instrumentors implement a dependency checking mechanism that runs before instrumentation:

1. Each instrumentor declares its dependencies via the `instrumentation_dependencies()` method
2. When `instrument()` is called, it checks for dependency conflicts using `_check_dependency_conflicts()`
3. If any conflicts are found, it logs an error and returns without instrumenting

```python
# Example of how OpenAIInstrumentor declares its dependency
_instruments = ("openai >= 0.27.0",)

def instrumentation_dependencies(self) -> Collection[str]:
    return _instruments
```

### Safety Notes

- The instrumentor is designed to be **safe** when dependencies are missing
- By default, the dependency check prevents instrumentation if the required package is missing or has version conflicts
- The instrumentor will log an error and gracefully exit without attempting to import missing packages
- Imports in `_instrument()` are done lazily (only when the method is called), which helps avoid import errors at module load time
- Only if you explicitly bypass the check with `skip_dep_check=True` would you encounter import errors

> To add custom instrumentation, please do so in the `third_party/opentelemetry` directory.



