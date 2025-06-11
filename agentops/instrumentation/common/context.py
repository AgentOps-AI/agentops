"""Common context management utilities for OpenTelemetry instrumentation.

This module provides utilities for managing OpenTelemetry context propagation
across different execution contexts, including:
- Context storage and retrieval
- Parent-child span relationships
- Trace continuity across async boundaries
- Context preservation in callbacks
"""

import weakref
from typing import Optional, Any, Dict
from contextlib import contextmanager

from opentelemetry import context as context_api
from opentelemetry import trace
from opentelemetry.trace import Span, Context, format_trace_id

from agentops.logging import logger


class ContextManager:
    """Manages OpenTelemetry context storage and propagation.

    This class provides thread-safe context management for maintaining
    span relationships across different execution contexts.
    """

    def __init__(self):
        """Initialize the context manager with weak reference dictionaries."""
        # Use weakref to prevent memory leaks
        self._span_contexts: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._trace_root_contexts: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._object_spans: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

    def store_span_context(self, key: Any, span: Span) -> Context:
        """Store a span's context for future reference.

        Args:
            key: The object to associate with this context
            span: The span whose context to store

        Returns:
            The stored context
        """
        context = trace.set_span_in_context(span)
        self._span_contexts[key] = context
        return context

    def store_trace_root_context(self, key: Any, context: Context):
        """Store a trace's root context for maintaining trace continuity.

        Args:
            key: The trace object to associate with this context
            context: The root context to store
        """
        self._trace_root_contexts[key] = context

    def get_parent_context(self, key: Any, fallback_to_current: bool = True) -> Optional[Context]:
        """Get the parent context for a given key.

        Args:
            key: The object whose parent context to retrieve
            fallback_to_current: Whether to fallback to current context if not found

        Returns:
            The parent context or current context if fallback is True
        """
        # First check if this object has a specific context
        if key in self._span_contexts:
            return self._span_contexts[key]

        # Then check if it has a trace root context
        if key in self._trace_root_contexts:
            return self._trace_root_contexts[key]

        # Fallback to current context if requested
        if fallback_to_current:
            return context_api.get_current()

        return None

    def associate_span_with_object(self, obj: Any, span: Span):
        """Associate a span with an object for lifecycle tracking.

        Args:
            obj: The object to associate with the span
            span: The span to associate
        """
        self._object_spans[obj] = span

    def get_span_for_object(self, obj: Any) -> Optional[Span]:
        """Get the span associated with an object.

        Args:
            obj: The object whose span to retrieve

        Returns:
            The associated span or None
        """
        return self._object_spans.get(obj)

    def clear_context(self, key: Any):
        """Clear all stored contexts for a given key.

        Args:
            key: The object whose contexts to clear
        """
        self._span_contexts.pop(key, None)
        self._trace_root_contexts.pop(key, None)
        self._object_spans.pop(key, None)

    @contextmanager
    def preserve_context(self, context: Optional[Context] = None):
        """Context manager to preserve OpenTelemetry context.

        Args:
            context: The context to preserve (uses current if None)

        Yields:
            The preserved context
        """
        if context is None:
            context = context_api.get_current()

        token = context_api.attach(context)
        try:
            yield context
        finally:
            context_api.detach(token)

    def debug_trace_info(self, span: Optional[Span] = None, label: str = ""):
        """Log debug information about the current trace.

        Args:
            span: The span to debug (uses current if None)
            label: A label to include in the debug output
        """
        if span is None:
            span = trace.get_current_span()

        span_context = span.get_span_context()
        trace_id = format_trace_id(span_context.trace_id)
        span_id = f"{span_context.span_id:016x}"

        logger.debug(
            f"Trace Debug {label}: "
            f"trace_id={trace_id}, "
            f"span_id={span_id}, "
            f"is_valid={span_context.is_valid}, "
            f"is_recording={span.is_recording()}"
        )


class SpanManager:
    """Utilities for creating and managing spans with consistent patterns."""

    @staticmethod
    def create_child_span(
        tracer: trace.Tracer,
        name: str,
        parent_context: Optional[Context] = None,
        kind: trace.SpanKind = trace.SpanKind.CLIENT,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Create a child span with proper context propagation.

        Args:
            tracer: The tracer to use for span creation
            name: The name of the span
            parent_context: The parent context (uses current if None)
            kind: The kind of span to create
            attributes: Initial attributes to set on the span

        Returns:
            The created span
        """
        if parent_context is None:
            parent_context = context_api.get_current()

        with tracer.start_as_current_span(name=name, context=parent_context, kind=kind, attributes=attributes) as span:
            return span

    @staticmethod
    @contextmanager
    def managed_span(
        tracer: trace.Tracer,
        name: str,
        context_manager: ContextManager,
        context_key: Any,
        kind: trace.SpanKind = trace.SpanKind.CLIENT,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Create a managed span that automatically handles context storage.

        Args:
            tracer: The tracer to use for span creation
            name: The name of the span
            context_manager: The context manager for storing contexts
            context_key: The key to associate with this span's context
            kind: The kind of span to create
            attributes: Initial attributes to set on the span

        Yields:
            The created span
        """
        parent_context = context_manager.get_parent_context(context_key)

        with tracer.start_as_current_span(name=name, context=parent_context, kind=kind, attributes=attributes) as span:
            # Store the span's context for future reference
            context_manager.store_span_context(context_key, span)
            yield span


# Global context manager instance for shared use
global_context_manager = ContextManager()
