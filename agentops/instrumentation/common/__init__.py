"""Common utilities for AgentOps instrumentation.

This module provides shared functionality for instrumenting various libraries,
including base classes, attribute management, metrics, and streaming utilities.
"""

from agentops.instrumentation.common.attributes import AttributeMap, _extract_attributes_from_mapping
from agentops.instrumentation.common.wrappers import _with_tracer_wrapper, WrapConfig, wrap, unwrap
from agentops.instrumentation.common.instrumentor import (
    InstrumentorConfig,
    CommonInstrumentor,
    create_wrapper_factory,
)
from agentops.instrumentation.common.metrics import StandardMetrics, MetricsRecorder
from agentops.instrumentation.common.span_management import (
    SpanAttributeManager,
    create_span,
    timed_span,
    StreamingSpanManager,
    extract_parent_context,
    safe_set_attribute,
    get_span_context_info,
)
from agentops.instrumentation.common.token_counting import (
    TokenUsage,
    TokenUsageExtractor,
    calculate_token_efficiency,
    calculate_cache_efficiency,
    set_token_usage_attributes,
)
from agentops.instrumentation.common.streaming import (
    BaseStreamWrapper,
    SyncStreamWrapper,
    AsyncStreamWrapper,
    create_stream_wrapper_factory,
    StreamingResponseHandler,
)
from agentops.instrumentation.common.version import (
    get_library_version,
    LibraryInfo,
)

__all__ = [
    # Attributes
    "AttributeMap",
    "_extract_attributes_from_mapping",
    # Wrappers
    "_with_tracer_wrapper",
    "WrapConfig",
    "wrap",
    "unwrap",
    # Instrumentor
    "InstrumentorConfig",
    "CommonInstrumentor",
    "create_wrapper_factory",
    # Metrics
    "StandardMetrics",
    "MetricsRecorder",
    # Span Management
    "SpanAttributeManager",
    "create_span",
    "timed_span",
    "StreamingSpanManager",
    "extract_parent_context",
    "safe_set_attribute",
    "get_span_context_info",
    # Token Counting
    "TokenUsage",
    "TokenUsageExtractor",
    "calculate_token_efficiency",
    "calculate_cache_efficiency",
    "set_token_usage_attributes",
    # Streaming
    "BaseStreamWrapper",
    "SyncStreamWrapper",
    "AsyncStreamWrapper",
    "create_stream_wrapper_factory",
    "StreamingResponseHandler",
    # Version
    "get_library_version",
    "LibraryInfo",
]
