"""Common utilities for OpenTelemetry instrumentation.

This module provides shared utilities for all AgentOps instrumentors:
- Base instrumentor with common patterns
- Context management and propagation
- Span lifecycle management
- Enhanced attribute handling
- Wrapper utilities
"""

# Existing exports
from .attributes import AttributeMap, _extract_attributes_from_mapping
from .wrappers import _with_tracer_wrapper, WrapConfig, wrap, unwrap
from .objects import get_uploaded_object_attributes

# New exports
from .base_instrumentor import EnhancedBaseInstrumentor
from .context import ContextManager, SpanManager, global_context_manager
from .span_lifecycle import (
    SpanLifecycleManager,
    TimingManager,
    RetryHandler,
    span_error_handler,
    async_span_error_handler,
)
from .attribute_handlers import (
    AttributeExtractor,
    LLMAttributeHandler,
    MessageAttributeHandler,
    StreamingAttributeHandler,
    create_composite_handler,
    with_attribute_filter,
)

__all__ = [
    # Existing
    "AttributeMap",
    "_extract_attributes_from_mapping",
    "_with_tracer_wrapper",
    "WrapConfig",
    "wrap",
    "unwrap",
    "get_uploaded_object_attributes",
    # New base instrumentor
    "EnhancedBaseInstrumentor",
    # Context management
    "ContextManager",
    "SpanManager",
    "global_context_manager",
    # Span lifecycle
    "SpanLifecycleManager",
    "TimingManager",
    "RetryHandler",
    "span_error_handler",
    "async_span_error_handler",
    # Attribute handlers
    "AttributeExtractor",
    "LLMAttributeHandler",
    "MessageAttributeHandler",
    "StreamingAttributeHandler",
    "create_composite_handler",
    "with_attribute_filter",
]
