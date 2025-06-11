# AgentOps Instrumentation Developer Guide

This comprehensive guide provides everything you need to implement OpenTelemetry instrumentation for LLM providers and related services in AgentOps.

## Table of Contents

1. [Architectural Overview](#architectural-overview)
2. [Prerequisites](#prerequisites)
3. [Available Instrumentors](#available-instrumentors)
4. [Quick Start Example](#quick-start-example)
5. [Implementation Guide](#implementation-guide)
6. [Configuration](#configuration)
7. [Testing Methodologies](#testing-methodologies)
8. [Debugging Techniques](#debugging-techniques)
9. [Error Handling](#error-handling)
10. [Best Practices](#best-practices)

### Key Components

- **EnhancedBaseInstrumentor**: Abstract base class providing common initialization, metrics, and lifecycle management
- **Context Management**: Thread-safe context propagation and span relationship management
- **Attribute Handlers**: Reusable extractors for common patterns (LLM requests, messages, streaming)
- **Span Lifecycle**: Consistent error handling, timing, and retry mechanisms
- **Wrapper Utilities**: Standardized method wrapping with OpenTelemetry integration

## Quick Start Example

### Using an Existing Instrumentor

```python
from agentops.instrumentation.openai import OpenAIInstrumentor
from agentops import init

# Initialize AgentOps
init(api_key="your-api-key")

# Initialize and instrument
instrumentor = OpenAIInstrumentor(
    enrich_assistant=True,  # Include assistant messages in spans
    enrich_token_usage=True,  # Include token usage in spans
    enable_trace_context_propagation=True,  # Enable trace context propagation
)
instrumentor.instrument()  # Uses the global AgentOps TracerProvider
```

## Implementation Guide

### Step 1: Create Your Instrumentor Class

Create a new file `agentops/instrumentation/your_provider/instrumentor.py`:

```python
"""YourProvider API Instrumentation for AgentOps

This module provides instrumentation for YourProvider API, implementing OpenTelemetry
instrumentation for model requests and responses.
"""

from typing import List, Collection, Dict, Any, Optional
from agentops.instrumentation.common import EnhancedBaseInstrumentor, WrapConfig
from agentops.instrumentation.your_provider import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.your_provider.attributes import (
    get_chat_attributes,
    get_completion_attributes,
)
from agentops.semconv import Meters


class YourProviderInstrumentor(EnhancedBaseInstrumentor):
    """An instrumentor for YourProvider's API.
    
    This instrumentor extends the EnhancedBaseInstrumentor to provide
    provider-specific instrumentation with automatic metric creation,
    error handling, and lifecycle management.
    """
    
    def __init__(self, config_option1: bool = True, config_option2: Optional[str] = None):
        super().__init__()
        self.config_option1 = config_option1
        self.config_option2 = config_option2
    
    @property
    def library_name(self) -> str:
        """Return the library name for tracer creation."""
        return LIBRARY_NAME
    
    @property
    def library_version(self) -> str:
        """Return the library version."""
        return LIBRARY_VERSION
    
    @property
    def wrapped_methods(self) -> List[WrapConfig]:
        """Define all methods to be wrapped for instrumentation."""
        return [
            # Chat completions
            WrapConfig(
                trace_name="your_provider.chat.completion",
                package="your_provider.resources.chat",
                class_name="Chat",
                method_name="create",
                handler=get_chat_attributes,
            ),
            # Async variant
            WrapConfig(
                trace_name="your_provider.chat.completion",
                package="your_provider.resources.chat",
                class_name="AsyncChat",
                method_name="create",
                handler=get_chat_attributes,
                is_async=True,
            ),
            # Add more methods as needed
        ]
    
    @property
    def supports_streaming(self) -> bool:
        """Indicate if this provider supports streaming responses."""
        return True  # Set to False if no streaming support
    
    def get_streaming_wrapper(self, tracer):
        """Return the sync streaming wrapper if supported."""
        if self.supports_streaming:
            from .stream_wrapper import create_streaming_wrapper
            return create_streaming_wrapper(tracer)
        return None
    
    def instrumentation_dependencies(self) -> Collection[str]:
        """Specify required package dependencies."""
        return ["your-provider >= 1.0.0"]
    
    def _create_provider_metrics(self, meter) -> Dict[str, Any]:
        """Create provider-specific metrics beyond the common ones."""
        return {
            "custom_metric": meter.create_counter(
                name="your_provider.custom_metric",
                unit="count",
                description="Description of your custom metric",
            ),
        }
```

### Step 2: Create Attribute Handlers

Create `agentops/instrumentation/your_provider/attributes.py`:

```python
"""Attribute extraction handlers for YourProvider instrumentation."""

from typing import Any, Dict, Optional, Tuple
from agentops.instrumentation.common import (
    AttributeMap,
    LLMAttributeHandler,
    MessageAttributeHandler,
    create_composite_handler,
)
from agentops.semconv import SpanAttributes, LLMRequestTypeValues

# Define provider-specific attribute mappings
YOUR_PROVIDER_REQUEST_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_REQUEST_CUSTOM_PARAM: "custom_param",
    # Add more mappings
}

YOUR_PROVIDER_RESPONSE_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_RESPONSE_CUSTOM_FIELD: "custom_field",
    # Add more mappings
}


def _extract_base_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract base attributes specific to YourProvider."""
    attributes = {
        SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value,
        SpanAttributes.LLM_SYSTEM: "YourProvider",
    }
    
    # Add provider-specific logic
    if kwargs and "streaming" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_STREAMING] = kwargs["streaming"]
    
    return attributes


def _extract_request_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract request attributes using common LLM handler."""
    if not kwargs:
        return {}
    
    # Use the common LLM handler with provider-specific mappings
    return LLMAttributeHandler.extract_request_attributes(
        kwargs,
        additional_mappings=YOUR_PROVIDER_REQUEST_ATTRIBUTES
    )


def _extract_messages(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract message content from request and response."""
    attributes = {}
    
    # Extract request messages
    if kwargs and "messages" in kwargs:
        messages = kwargs["messages"]
        # Transform to standard format if needed
        formatted_messages = _format_messages(messages)
        
        message_attrs = MessageAttributeHandler.extract_messages(
            formatted_messages,
            attribute_type="prompt"
        )
        attributes.update(message_attrs)
    
    # Extract response messages
    if return_value:
        response_messages = _extract_response_messages(return_value)
        if response_messages:
            completion_attrs = MessageAttributeHandler.extract_messages(
                response_messages,
                attribute_type="completion"
            )
            attributes.update(completion_attrs)
    
    return attributes


def _extract_response_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract response attributes using common handler."""
    if not return_value:
        return {}
    
    # Convert response to dict if needed
    response_dict = _convert_to_dict(return_value)
    
    return LLMAttributeHandler.extract_response_attributes(
        response_dict,
        additional_mappings=YOUR_PROVIDER_RESPONSE_ATTRIBUTES
    )


# Create the main composite handler
get_chat_attributes = create_composite_handler(
    _extract_base_attributes,
    _extract_request_attributes,
    _extract_messages,
    _extract_response_attributes,
)
```

### Step 3: Handle Streaming (if applicable)

Create `agentops/instrumentation/your_provider/stream_wrapper.py`:

```python
"""Streaming response wrapper for YourProvider."""

from typing import Any, AsyncIterator, Iterator
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from agentops.instrumentation.common import (
    SpanLifecycleManager,
    StreamingAttributeHandler,
    global_context_manager,
)


def create_streaming_wrapper(tracer: trace.Tracer):
    """Create a wrapper for streaming responses."""
    
    def wrapper(wrapped, instance, args, kwargs):
        # Start span for the streaming operation
        with tracer.start_as_current_span(
            "your_provider.chat.stream",
            kind=SpanKind.CLIENT,
        ) as span:
            # Mark as streaming
            span.set_attribute("gen_ai.request.streaming", True)
            
            # Get the stream
            stream = wrapped(*args, **kwargs)
            
            # Create streaming handler
            handler = StreamingAttributeHandler.create_streaming_handler(
                span_attribute_prefix="stream"
            )
            
            # Wrap the stream
            return StreamWrapper(stream, span, handler)
    
    return wrapper


class StreamWrapper:
    """Wrapper for streaming responses that captures incremental data."""
    
    def __init__(self, stream, span, handler):
        self.stream = stream
        self.span = span
        self.handler = handler
        self.chunk_index = 0
        self.accumulated_content = ""
    
    def __iter__(self):
        try:
            for chunk in self.stream:
                # Extract and accumulate content
                content = self._extract_content(chunk)
                if content:
                    self.accumulated_content += content
                
                # Update span with chunk data
                attributes = self.handler(
                    chunk,
                    self.chunk_index,
                    self.accumulated_content
                )
                
                for key, value in attributes.items():
                    self.span.set_attribute(key, value)
                
                self.chunk_index += 1
                yield chunk
                
        except Exception as e:
            SpanLifecycleManager.record_exception(self.span, e)
            raise
        finally:
            # Final attributes
            self.span.set_attribute("stream.total_chunks", self.chunk_index)
            self.span.set_attribute("stream.final_content", self.accumulated_content)
            SpanLifecycleManager.set_success_status(self.span)
    
    def _extract_content(self, chunk):
        """Extract content from a chunk - implement based on provider format."""
        # Example implementation
        if hasattr(chunk, 'choices') and chunk.choices:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content'):
                return delta.content
        return ""
```

### Step 4: Set Up Module Structure

Create the module structure:

```
agentops/instrumentation/your_provider/
├── __init__.py
├── instrumentor.py
├── attributes.py
├── stream_wrapper.py (if streaming is supported)
└── README.md
```

`__init__.py`:
```python
"""YourProvider API instrumentation."""

from agentops.logging import logger


def get_version() -> str:
    """Get the version of YourProvider SDK."""
    try:
        from importlib.metadata import version
        return version("your-provider")
    except ImportError:
        logger.debug("Could not find YourProvider SDK version")
        return "unknown"


LIBRARY_NAME = "your_provider"
LIBRARY_VERSION = get_version()

from agentops.instrumentation.your_provider.instrumentor import YourProviderInstrumentor

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "YourProviderInstrumentor",
]
```

## Testing Methodologies

### Unit Tests

Create `tests/instrumentation/test_your_provider.py`:

```python
import pytest
from unittest.mock import Mock, patch
from agentops.instrumentation.your_provider import YourProviderInstrumentor
from agentops.instrumentation.your_provider.attributes import get_chat_attributes


class TestYourProviderInstrumentor:
    """Test suite for YourProvider instrumentor."""
    
    def test_initialization(self):
        """Test instrumentor initialization."""
        instrumentor = YourProviderInstrumentor(
            enrich_messages=True,
            enrich_token_usage=False
        )
        assert instrumentor.library_name == "your_provider"
        assert instrumentor.supports_streaming is True
    
    def test_wrapped_methods(self):
        """Test wrapped methods configuration."""
        instrumentor = YourProviderInstrumentor()
        methods = instrumentor.wrapped_methods
        
        # Verify expected methods are configured
        method_names = [(m.class_name, m.method_name) for m in methods]
        assert ("Chat", "create") in method_names
        assert ("AsyncChat", "create") in method_names
    
    def test_attribute_extraction(self):
        """Test attribute extraction from API calls."""
        # Mock request
        kwargs = {
            "model": "your-model-v1",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ],
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        # Mock response
        response = Mock()
        response.id = "resp-123"
        response.model = "your-model-v1"
        response.usage = Mock(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        )
        
        # Extract attributes
        attributes = get_chat_attributes(
            kwargs=kwargs,
            return_value=response
        )
        
        # Verify request attributes
        assert attributes["gen_ai.request.model"] == "your-model-v1"
        assert attributes["gen_ai.request.temperature"] == 0.7
        assert attributes["gen_ai.request.max_tokens"] == 100
        
        # Verify response attributes
        assert attributes["gen_ai.response.id"] == "resp-123"
        assert attributes["gen_ai.usage.prompt_tokens"] == 10
        assert attributes["gen_ai.usage.completion_tokens"] == 5
        assert attributes["gen_ai.usage.total_tokens"] == 15
    
    @pytest.mark.asyncio
    async def test_async_instrumentation(self):
        """Test async method instrumentation."""
        # Test async wrapped methods work correctly
        pass


class TestStreamingWrapper:
    """Test streaming functionality."""
    
    def test_stream_wrapper(self):
        """Test streaming response wrapper."""
        # Mock stream chunks
        chunks = [
            Mock(choices=[Mock(delta=Mock(content="Hello"))]),
            Mock(choices=[Mock(delta=Mock(content=" world"))]),
            Mock(choices=[Mock(delta=Mock(content="!"))]),
        ]
        
        # Test wrapper accumulates content correctly
        # Test span attributes are set
        # Test error handling in stream
```
### 1. Use Common Utilities

Always leverage the common utilities instead of reimplementing:

```python
# Good - uses common handler
from agentops.instrumentation.common import LLMAttributeHandler

attributes = LLMAttributeHandler.extract_request_attributes(kwargs)

# Bad - reimplements extraction
attributes = {}
if "model" in kwargs:
    attributes["gen_ai.request.model"] = kwargs["model"]
# ... etc
```

### 2. Consistent Attribute Naming

Follow OpenTelemetry semantic conventions:

```python
# Good - uses semantic conventions
from agentops.semconv import SpanAttributes

attributes[SpanAttributes.LLM_REQUEST_MODEL] = model

# Bad - custom attribute names
attributes["model_name"] = model
```
### 3. Documentation

Document your instrumentor thoroughly:

```python
class YourProviderInstrumentor(EnhancedBaseInstrumentor):
    """Instrumentor for YourProvider API.
    
    This instrumentor provides OpenTelemetry instrumentation for YourProvider,
    capturing request/response data, token usage, and streaming responses.
    
    Features:
        - Automatic span creation for all API calls
        - Token usage tracking
        - Streaming response support
        - Error tracking and retry logic
        - Context propagation across async calls
    
    Example:
        >>> from agentops.instrumentation.your_provider import YourProviderInstrumentor
        >>> instrumentor = YourProviderInstrumentor(enrich_token_usage=True)
        >>> instrumentor.instrument()
        >>> 
        >>> # Your provider will now be instrumented
        >>> client = YourProvider()
        >>> response = client.chat.create(model="...", messages=[...])
    
    Args:
        enrich_token_usage: Whether to capture token usage metrics
        enrich_messages: Whether to capture message content
        capture_streaming: Whether to instrument streaming responses
    """
```

## Adding Custom Instrumentation

If you need to add instrumentation outside the standard patterns:

```python
from opentelemetry import trace
from agentops.instrumentation.common import SpanLifecycleManager

def custom_operation():
    """Example of manual instrumentation."""
    tracer = trace.get_tracer("your_provider", "1.0.0")
    
    with tracer.start_as_current_span("custom.operation") as span:
        try:
            # Set custom attributes
            span.set_attribute("custom.attribute", "value")
            
            # Your operation
            result = do_something()
            
            # Record success
            SpanLifecycleManager.set_success_status(span, "Operation completed")
            
            return result
            
        except Exception as e:
            # Record error
            SpanLifecycleManager.record_exception(span, e)
            raise
```

## Troubleshooting

## Contributing

When contributing a new instrumentor:

1. Follow the patterns established in this guide
2. Include comprehensive tests
3. Update the PROVIDERS dictionary
4. Submit PR with description of the provider and its features

For more information, see the [CONTRIBUTING.md](../../CONTRIBUTING.md) file.
