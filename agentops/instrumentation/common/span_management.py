"""Common span management utilities for AgentOps instrumentation.

This module provides utilities for creating and managing spans with
consistent attributes and error handling.
"""

import time
from contextlib import contextmanager
from typing import Optional, Dict, Any, Callable, Tuple
from functools import wraps

from opentelemetry.trace import Tracer, Span, SpanKind, Status, StatusCode, get_current_span
from opentelemetry.sdk.resources import SERVICE_NAME, TELEMETRY_SDK_NAME, DEPLOYMENT_ENVIRONMENT
from opentelemetry import context as context_api

from agentops.logging import logger
from agentops.semconv import CoreAttributes


class SpanAttributeManager:
    """Manages common span attributes across instrumentations."""

    def __init__(self, service_name: str = "agentops", deployment_environment: str = "production"):
        self.service_name = service_name
        self.deployment_environment = deployment_environment

    def set_common_attributes(self, span: Span):
        """Set common attributes on a span."""
        span.set_attribute(TELEMETRY_SDK_NAME, "agentops")
        span.set_attribute(SERVICE_NAME, self.service_name)
        span.set_attribute(DEPLOYMENT_ENVIRONMENT, self.deployment_environment)

    def set_config_tags(self, span: Span):
        """Set tags from AgentOps config on a span."""
        # Import locally to avoid circular dependency
        from agentops import get_client

        client = get_client()
        if client and client.config.default_tags and len(client.config.default_tags) > 0:
            tag_list = list(client.config.default_tags)
            span.set_attribute(CoreAttributes.TAGS, tag_list)


@contextmanager
def create_span(
    tracer: Tracer,
    name: str,
    kind: SpanKind = SpanKind.CLIENT,
    attributes: Optional[Dict[str, Any]] = None,
    set_common_attributes: bool = True,
    attribute_manager: Optional[SpanAttributeManager] = None,
):
    """Context manager for creating spans with consistent error handling.

    Args:
        tracer: The tracer to use for creating the span
        name: The name of the span
        kind: The kind of span to create
        attributes: Initial attributes to set on the span
        set_common_attributes: Whether to set common attributes
        attribute_manager: Optional attribute manager for setting common attributes

    Yields:
        The created span
    """
    with tracer.start_as_current_span(name, kind=kind, attributes=attributes or {}) as span:
        try:
            if set_common_attributes and attribute_manager:
                attribute_manager.set_common_attributes(span)
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            logger.error(f"Error in span {name}: {e}")
            raise


def timed_span(tracer: Tracer, name: str, record_duration: Optional[Callable[[float], None]] = None, **span_kwargs):
    """Decorator for creating timed spans around functions.

    Args:
        tracer: The tracer to use
        name: The name of the span
        record_duration: Optional callback to record duration
        **span_kwargs: Additional arguments for span creation
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            with create_span(tracer, name, **span_kwargs):
                result = func(*args, **kwargs)
                if record_duration:
                    duration = time.time() - start_time
                    record_duration(duration)
                return result

        return wrapper

    return decorator


class StreamingSpanManager:
    """Manages spans for streaming operations."""

    def __init__(self, tracer: Tracer):
        self.tracer = tracer
        self._active_spans: Dict[Any, Span] = {}

    def start_streaming_span(self, stream_id: Any, name: str, **span_kwargs) -> Span:
        """Start a span for a streaming operation."""
        span = self.tracer.start_span(name, **span_kwargs)
        self._active_spans[stream_id] = span
        return span

    def get_streaming_span(self, stream_id: Any) -> Optional[Span]:
        """Get an active streaming span."""
        return self._active_spans.get(stream_id)

    def end_streaming_span(self, stream_id: Any, status: Optional[Status] = None):
        """End a streaming span."""
        span = self._active_spans.pop(stream_id, None)
        if span:
            if status:
                span.set_status(status)
            else:
                span.set_status(Status(StatusCode.OK))
            span.end()


def extract_parent_context(parent_span: Optional[Span] = None) -> Any:
    """Extract parent context for span creation.

    Args:
        parent_span: Optional parent span to use

    Returns:
        Context to use as parent
    """
    if parent_span:
        from opentelemetry.trace import set_span_in_context

        return set_span_in_context(parent_span)
    return context_api.get_current()


def safe_set_attribute(span: Span, key: str, value: Any, max_length: int = 1000):
    """Safely set an attribute on a span, handling None values and truncating long strings."""
    if value is None:
        return

    if isinstance(value, str) and len(value) > max_length:
        value = value[: max_length - 3] + "..."

    try:
        span.set_attribute(key, value)
    except Exception as e:
        logger.debug(f"Failed to set span attribute {key}: {e}")


def get_span_context_info(span: Optional[Span] = None) -> Tuple[str, str]:
    """Get trace and span IDs from a span for debugging.

    Returns:
        Tuple of (trace_id, span_id) as strings
    """
    if not span:
        span = get_current_span()

    span_context = span.get_span_context()
    trace_id = format(span_context.trace_id, "032x") if span_context.trace_id else "unknown"
    span_id = format(span_context.span_id, "016x") if span_context.span_id else "unknown"

    return trace_id, span_id
