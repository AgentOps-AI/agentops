# AgentOps Instrumentation

This package provides OpenTelemetry instrumentation for various LLM providers and related services.

## Available Instrumentors

- **OpenAI** (`v0.27.0+` and `v1.0.0+`)
- **Anthropic** (`v0.7.0+`)
- **Google GenAI** (`v0.1.0+`)
- **IBM WatsonX AI** (`v0.1.0+`)
- **CrewAI** (`v0.56.0+`)
- **AG2/AutoGen** (`v0.3.2+`)
- **Google ADK** (`v0.1.0+`)
- **Agno** (`v0.0.1+`)
- **Mem0** (`v0.1.0+`)
- **smolagents** (`v0.1.0+`)

## Common Module Usage

The `agentops.instrumentation.common` module provides shared utilities for creating instrumentations:

### Base Instrumentor

Use `CommonInstrumentor` for creating new instrumentations:

```python
from agentops.instrumentation.common import CommonInstrumentor, InstrumentorConfig, WrapConfig

class MyInstrumentor(CommonInstrumentor):
    def __init__(self):
        config = InstrumentorConfig(
            library_name="my-library",
            library_version="1.0.0",
            wrapped_methods=[
                WrapConfig(
                    trace_name="my.method",
                    package="my_library.module",
                    class_name="MyClass",
                    method_name="my_method",
                    handler=my_attribute_handler
                )
            ],
            dependencies=["my-library >= 1.0.0"]
        )
        super().__init__(config)
```

### Attribute Handlers

Create attribute handlers to extract data from method calls:

```python
from agentops.instrumentation.common import AttributeMap

def my_attribute_handler(args=None, kwargs=None, return_value=None) -> AttributeMap:
    attributes = {}
    
    if kwargs and "model" in kwargs:
        attributes["llm.request.model"] = kwargs["model"]
    
    if return_value and hasattr(return_value, "usage"):
        attributes["llm.usage.total_tokens"] = return_value.usage.total_tokens
    
    return attributes
```

### Span Management

Use the span management utilities for consistent span creation:

```python
from agentops.instrumentation.common import create_span, SpanAttributeManager

# Create an attribute manager
attr_manager = SpanAttributeManager(service_name="my-service")

# Use the create_span context manager
with create_span(
    tracer,
    "my.operation",
    attributes={"my.attribute": "value"},
    attribute_manager=attr_manager
) as span:
    # Your operation code here
    pass
```

### Token Counting

Use the token counting utilities for consistent token usage extraction:

```python
from agentops.instrumentation.common import TokenUsageExtractor, set_token_usage_attributes

# Extract token usage from a response
usage = TokenUsageExtractor.extract_from_response(response)

# Set token usage attributes on a span
set_token_usage_attributes(span, response)
```

### Streaming Support

Use streaming utilities for handling streaming responses:

```python
from agentops.instrumentation.common import create_stream_wrapper_factory, StreamingResponseHandler

# Create a stream wrapper factory
wrapper = create_stream_wrapper_factory(
    tracer,
    "my.stream",
    extract_chunk_content=StreamingResponseHandler.extract_generic_chunk_content,
    initial_attributes={"stream.type": "text"}
)

# Apply to streaming methods
wrap_function_wrapper("my_module", "stream_method", wrapper)
```

### Metrics

Use standard metrics for consistency across instrumentations:

```python
from agentops.instrumentation.common import StandardMetrics, MetricsRecorder

# Create standard metrics
metrics = StandardMetrics.create_standard_metrics(meter)

# Use the metrics recorder
recorder = MetricsRecorder(metrics)
recorder.record_token_usage(prompt_tokens=100, completion_tokens=50)
recorder.record_duration(1.5)
```

## Creating a New Instrumentor

1. Create a new directory under `agentops/instrumentation/` for your provider
2. Create an `__init__.py` file with version information
3. Create an `instrumentor.py` file extending `CommonInstrumentor`
4. Create attribute handlers in an `attributes/` subdirectory
5. Add your instrumentor to the main `__init__.py` configuration

Example structure:
```
agentops/instrumentation/
├── my_provider/
│   ├── __init__.py
│   ├── instrumentor.py
│   └── attributes/
│       ├── __init__.py
│       └── handlers.py
```

## Best Practices

1. **Use Common Utilities**: Leverage the common module for consistency
2. **Follow Semantic Conventions**: Use attributes from `agentops.semconv`
3. **Handle Errors Gracefully**: Wrap operations in try-except blocks
4. **Support Async**: Provide both sync and async method wrapping
5. **Document Attributes**: Comment on what attributes are captured
6. **Test Thoroughly**: Write unit tests for your instrumentor

## Examples

See the `examples/` directory for usage examples of each instrumentor.
