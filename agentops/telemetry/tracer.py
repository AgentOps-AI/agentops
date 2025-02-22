"""Session tracing module for AgentOps.

This module provides automatic tracing capabilities for AgentOps sessions.
Each session represents a root span, with all operations within the session
tracked as child spans.
"""

from __future__ import annotations

import atexit
import threading
from typing import TYPE_CHECKING, Any, Dict, Optional
from weakref import WeakValueDictionary

from opentelemetry import context, trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import \
    TraceContextTextMapPropagator

from agentops.logging import logger
from agentops.session import session_ended, session_started

from .exporters import RegularEventExporter
from .processors import LiveSpanProcessor

if TYPE_CHECKING:
    from agentops.session.session import Session

# Use WeakValueDictionary to allow tracer garbage collection
_session_tracers: WeakValueDictionary[str, "SessionTracer"] = WeakValueDictionary()


class SessionTracer:
    """Core session tracing functionality.

    Handles the session-level tracing context and span management.
    A session IS a root span - all operations within the session are automatically
    tracked as child spans.
    """

    def __init__(self, session: Session):
        """Initialize session tracer with provider and processors."""
        self.session_id = str(session.session_id)
        self._is_ended = False
        self._shutdown_lock = threading.Lock()

        # Initialize provider if needed
        provider = trace.get_tracer_provider()
        if not isinstance(provider, TracerProvider):
            provider = TracerProvider(resource=Resource({SERVICE_NAME: "agentops", "session.id": self.session_id}))
            trace.set_tracer_provider(provider)

        # Set up processor and exporter
        processor = LiveSpanProcessor(RegularEventExporter(session))
        provider.add_span_processor(processor)

        # Initialize tracer and root span
        self.tracer = provider.get_tracer("agentops.session")
        self._root_span = self.tracer.start_span(
            "session.lifecycle", attributes={"session.id": self.session_id, "session.type": "root"}
        )
        self._context = trace.set_span_in_context(self._root_span)

        # Store for cleanup
        _session_tracers[self.session_id] = self
        atexit.register(self.shutdown)

        logger.debug(f"[{self.session_id}] Session tracer initialized")

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> trace.Span:
        """Start a new child span in the session context."""
        if self._is_ended:
            raise RuntimeError("Cannot start span on ended session")

        if self._context is None:
            raise RuntimeError("No active session context")

        attributes = attributes or {}
        attributes["session.id"] = self.session_id

        return self.tracer.start_span(name, context=self._context, attributes=attributes)

    def inject_context(self, carrier: Dict[str, str]) -> None:
        """Inject current context into carrier for propagation."""
        if self._context:
            TraceContextTextMapPropagator().inject(carrier, self._context)

    def extract_context(self, carrier: Dict[str, str]) -> Optional[context.Context]:
        """Extract context from carrier."""
        return TraceContextTextMapPropagator().extract(carrier)

    def shutdown(self) -> None:
        """Shutdown and cleanup resources."""
        with self._shutdown_lock:
            if self._is_ended:
                return

            logger.debug(f"[{self.session_id}] Shutting down session tracer")

            if self._root_span:
                self._root_span.end()

            provider = trace.get_tracer_provider()
            if isinstance(provider, TracerProvider):
                try:
                    provider.force_flush()
                    provider.shutdown()
                except Exception as e:
                    logger.debug(f"[{self.session_id}] Error during shutdown: {e}")

            self._is_ended = True
            logger.debug(f"[{self.session_id}] Session tracer shutdown complete")

    def __del__(self):
        """Ensure cleanup on garbage collection."""
        self.shutdown()


@session_started.connect
def setup_session_tracer(sender: Session, **kwargs):
    """Set up and start session tracing."""
    try:
        tracer = SessionTracer(sender)
        sender._tracer = tracer
        logger.debug(f"[{sender.session_id}] Session tracing started")
    except Exception as e:
        logger.error(f"[{sender.session_id}] Failed to initialize session tracer: {e}")
        raise


@session_ended.connect
def cleanup_session_tracer(sender: Session, **kwargs):
    """Clean up session tracing."""
    session_id = str(sender.session_id)
    if session_id in _session_tracers:
        tracer = _session_tracers.pop(session_id)
        tracer.shutdown()
        logger.debug(f"[{session_id}] Session tracing cleaned up")


def get_session_tracer(session_id: str) -> Optional[SessionTracer]:
    """Get tracer for a session."""
    return _session_tracers.get(str(session_id))
