# Contributing to AgentOps Instrumentation

## Adding a New Instrumentor

### 1. Determine the Category

- **Providers**: LLM API providers (OpenAI, Anthropic, etc.)
- **Frameworks**: Agent frameworks (CrewAI, AutoGen, etc.)
- **Utilities**: Infrastructure/utility modules (threading, logging, etc.)

### 2. Create Module Structure

```
category_name/
└── your_module/
    ├── __init__.py
    ├── instrumentor.py      # Main instrumentor class
    ├── attributes/          # Attribute extraction functions
    │   ├── __init__.py
    │   └── common.py
    └── stream_wrapper.py    # If streaming is supported
```

### 3. Implement the Instrumentor

```python
from agentops.instrumentation.common.base_instrumentor import AgentOpsBaseInstrumentor
from agentops.instrumentation.common.wrappers import WrapConfig

class YourInstrumentor(AgentOpsBaseInstrumentor):
    def instrumentation_dependencies(self):
        return ["your-package >= 1.0.0"]
    
    def _init_wrapped_methods(self):
        return [
            WrapConfig(
                trace_name="your_module.operation",
                package="your_package.module",
                class_name="YourClass",
                method_name="method",
                handler=your_attribute_handler,
            ),
        ]
```

### 4. Implement Attribute Handlers

```python
# In attributes/common.py
def your_attribute_handler(args, kwargs, return_value=None):
    attributes = {}
    # Extract relevant attributes
    return attributes
```

### 5. Add Streaming Support (if applicable)

```python
from agentops.instrumentation.common.streaming import StreamingResponseWrapper

class YourStreamWrapper(StreamingResponseWrapper):
    def _process_chunk(self, chunk):
        # Process streaming chunks
        pass
```

### 6. Write Tests

Add tests in `tests/instrumentation/test_your_module.py`

### 7. Update Documentation

- Add your module to the main README.md
- Create a README.md in your module directory
- Document any special features or requirements

## Code Standards

- Use type hints
- Follow PEP 8
- Add docstrings to all public methods
- Handle errors gracefully
- Log at appropriate levels

## Testing

Run tests before submitting:
```bash
pytest tests/instrumentation/test_your_module.py
```

## Submitting

1. Create a feature branch
2. Make your changes
3. Add tests
4. Update documentation
5. Submit a pull request
