"""Session tracing module for AgentOps.

This module provides automatic tracing capabilities for AgentOps sessions through signal handlers.
It manages session-specific tracers and ensures proper cleanup when sessions end.

The tracers capture:
    - Session ID for all operations
    - Session state transitions
    - Operation timing
    - Error states and reasons
"""

from __future__ import annotations

import atexit
import contextlib
from typing import TYPE_CHECKING, Any, Collection, Dict, Optional, Sequence
from weakref import WeakValueDictionary

from opentelemetry import context, trace
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import (ReadableSpan, Span, SpanProcessor, Tracer,
                                     TracerProvider)
from opentelemetry.sdk.trace.export import (BatchSpanProcessor,
                                            SimpleSpanProcessor)
from opentelemetry.trace import NonRecordingSpan, SpanContext
from opentelemetry.trace.propagation.tracecontext import \
    TraceContextTextMapPropagator
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider  # The SDK implementation

from agentops.instrumentation.session.exporters import (
    RegularEventExporter, SessionLifecycleExporter)
from agentops.logging import logger
from agentops.session import session_ended, session_started

if TYPE_CHECKING:
    from agentops.session.session import Session

# Use WeakValueDictionary to allow tracer garbage collection
_session_tracers: WeakValueDictionary[str, "SessionInstrumentor"] = WeakValueDictionary()

_instruments = ("agentops >= 0.1.0",)


class SessionTracer:
    """Core session tracing functionality.

    Handles the session-level tracing context and span management.
    """

    session: Session
    tracer: trace.Tracer

    def __init__(self, session_id: str, tracer: trace.Tracer):
        self.session_id = session_id
        self.tracer = tracer
        self._root_span: Span | None = None  # Use union type syntax
        self._context: context.Context | None = None

    @contextlib.contextmanager
    def start_root_span(self):
        """Start and manage the root session span."""
        if self._root_span is not None:
            raise RuntimeError("Root span already exists")

        root_span = self.tracer.start_span(
            "session.lifecycle", attributes={"session.id": self.session_id, "session.type": "root"}
        )
        self._root_span = root_span  # type: ignore
        self._context = trace.set_span_in_context(root_span)

        try:
            yield root_span
        finally:
            root_span.end()
            self._root_span = None
            self._context = None

    @contextlib.contextmanager
    def start_operation(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Start an operation span as child of root span."""
        if self._context is None:
            raise RuntimeError("No active session context")

        attributes = attributes or {}
        attributes["session.id"] = self.session_id

        token = context.attach(self._context)
        try:
            with self.tracer.start_as_current_span(name, attributes=attributes) as span:
                yield span
        finally:
            context.detach(token)

    def inject_context(self, carrier: Dict[str, str]):
        """Inject current context into carrier for propagation."""
        if self._context:
            TraceContextTextMapPropagator().inject(carrier, self._context)

    def extract_context(self, carrier: Dict[str, str]) -> Optional[context.Context]:
        """Extract context from carrier."""
        return TraceContextTextMapPropagator().extract(carrier)


class SessionInstrumentor:
    """OpenTelemetry instrumentor for session tracing."""

    _is_instrumented = False

    def __init__(self, session: "Session"):
        self.session = session
        self.otel_provider: SDKTracerProvider | None = None  # Change to SDK type since we need SDK features
        self.session_tracer: SessionTracer | None = None
        self.processors: list[SpanProcessor] = []

        self.instrument()
        if self.session_tracer is None:
            raise RuntimeError("Failed to initialize session tracer")

        _session_tracers[str(session.session_id)] = self
        atexit.register(self.shutdown)

    def instrument(self, **kwargs):
        """Initialize OTEL instrumentation."""
        logger.debug(f"Initializing tracer for session {self.session.session_id}")

        # Get or create provider
        provider = trace.get_tracer_provider()
        if isinstance(provider, SDKTracerProvider):
            self.otel_provider = provider
        else:
            # Only create new provider if we don't have a valid SDK provider
            self.otel_provider = SDKTracerProvider(
                resource=Resource({"service.name": "agentops", "session.id": str(self.session.session_id)})
            )
            # Don't override if we already have an SDK provider
            if not isinstance(trace.get_tracer_provider(), SDKTracerProvider):
                trace.set_tracer_provider(self.otel_provider)

        # Configure processors
        lifecycle_processor = BatchSpanProcessor(SessionLifecycleExporter(self.session))
        regular_processor = BatchSpanProcessor(RegularEventExporter(self.session))

        self.processors.extend([lifecycle_processor, regular_processor])
        self.otel_provider.add_span_processor(lifecycle_processor)
        self.otel_provider.add_span_processor(regular_processor)

        # Create session tracer
        otel_tracer = self.otel_provider.get_tracer("agentops.session")
        self.session_tracer = SessionTracer(str(self.session.session_id), otel_tracer)
        
        SessionInstrumentor._is_instrumented = True
        logger.debug("Session tracer ready")
        self.session._tracer = self.session_tracer

    def uninstrument(self, **kwargs):
        """Clean up instrumentation."""
        self.shutdown()
        SessionInstrumentor._is_instrumented = False

    def shutdown(self):
        """Shutdown and cleanup resources."""
        logger.debug("Shutting down session tracer")
        for processor in self.processors:
            processor.shutdown()
        if isinstance(self.otel_provider, SDKTracerProvider):  # Type check before SDK operations
            self.otel_provider.shutdown()
        logger.debug("Session tracer shutdown complete")

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        return _instruments


@session_started.connect
def setup_session_tracer(sender: Session, **kwargs):
    """Set up and start session tracing."""
    try:
        instrumentor = SessionInstrumentor(sender)
        instrumentor.instrument()
        logger.debug(f"Session tracing started for {sender.session_id}")
    except Exception as e:
        logger.error(f"Failed to initialize session tracer: {e}")
        raise


@session_ended.connect
def cleanup_session_tracer(sender: Session, **kwargs):
    """Clean up session tracing."""
    session_id = str(sender.session_id)
    if session_id in _session_tracers:
        tracer = _session_tracers.pop(session_id)
        tracer.uninstrument()
        logger.debug(f"Session tracing cleaned up for {session_id}")


def get_session_tracer(session_id: str) -> Optional[SessionTracer]:
    """Get tracer for a session."""
    instrumentor = _session_tracers.get(str(session_id))
    return instrumentor.session_tracer if instrumentor else None


# Add a custom filtering processor
class FilteringSpanProcessor(SpanProcessor):
    """Processor that filters spans based on their names"""

    def __init__(
        self,
        wrapped_processor: SpanProcessor,
        span_names: Optional[Sequence[str]] = None,
        exclude_span_names: Optional[Sequence[str]] = None,
    ):
        self.processor = wrapped_processor
        self.span_names = set(span_names or [])
        self.exclude_span_names = set(exclude_span_names or [])

    def on_start(self, span: Span, parent_context=None) -> None:
        self.processor.on_start(span, parent_context)

    def on_end(self, span: Span) -> None:
        if span.name in self.exclude_span_names:
            return
        if not self.span_names or span.name in self.span_names:
            self.processor.on_end(span)

    def shutdown(self) -> None:
        self.processor.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush with default timeout."""
        return self.processor.force_flush(timeout_millis)
