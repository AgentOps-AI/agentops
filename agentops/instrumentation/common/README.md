# AgentOps Instrumentation Common Module

The `agentops.instrumentation.common` module provides shared utilities for OpenTelemetry instrumentation across different LLM service providers.

## Core Components

### Attribute Handler Example

Attribute handlers extract data from method inputs and outputs:

```python
from typing import Optional, Any, Tuple, Dict
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes

def my_attribute_handler(args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None) -> AttributeMap:
    attributes = {}
    
    # Extract attributes from kwargs (method inputs)
    if kwargs:
        if "model" in kwargs:
            attributes[SpanAttributes.MODEL_NAME] = kwargs["model"]
        # ...
    
    # Extract attributes from return value (method outputs)
    if return_value:
        if hasattr(return_value, "model"):
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = return_value.model
        # ...
    
    return attributes
```

### `WrapConfig` Class

Config object defining how a method should be wrapped:

```python
from agentops.instrumentation.common.wrappers import WrapConfig
from opentelemetry.trace import SpanKind

config = WrapConfig(
    trace_name="llm.completion",    # Name that will appear in trace spans
    package="openai.resources",     # Path to the module containing the class
    class_name="Completions",       # Name of the class containing the method
    method_name="create",           # Name of the method to wrap
    handler=my_attribute_handler,   # Function that extracts attributes
    span_kind=SpanKind.CLIENT       # Type of span to create
)
```

### Wrapping/Unwrapping Methods

```python
from opentelemetry.trace import get_tracer
from agentops.instrumentation.common.wrappers import wrap, unwrap

# Create a tracer and wrap a method
tracer = get_tracer("openai", "0.0.0")
wrap(config, tracer)

# Later, unwrap the method
unwrap(config)
```

