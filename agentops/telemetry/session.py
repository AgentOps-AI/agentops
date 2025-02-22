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
from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
    OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor,
                                            SimpleSpanProcessor)
from opentelemetry.trace.propagation.tracecontext import \
    TraceContextTextMapPropagator

from agentops.logging import logger
from agentops.session.signals import session_ended, session_started

from .exporters import RegularEventExporter
from .processors import LiveSpanProcessor

if TYPE_CHECKING:
    from agentops.session.session import Session

# Use WeakValueDictionary to allow tracer garbage collection
_session_tracers: WeakValueDictionary[str, "SessionTelemetry"] = WeakValueDictionary()

# Global TracerProvider instance
_tracer_provider: Optional[TracerProvider] = None


def get_tracer_provider() -> TracerProvider:
    """Get or create the global TracerProvider."""
    global _tracer_provider
    if _tracer_provider is None:
        _tracer_provider = TracerProvider(resource=Resource({SERVICE_NAME: "agentops"}))
        trace.set_tracer_provider(_tracer_provider)
    return _tracer_provider


@session_started.connect
def setup_session_tracer(sender: Session, **kwargs):
    """Set up and start session tracing."""
    try:
        tracer = SessionTelemetry(sender)
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


def get_session_tracer(session_id: str) -> Optional[SessionTelemetry]:
    """Get tracer for a session."""
    return _session_tracers.get(str(session_id))


class SessionTelemetry:
    """Core session tracing functionality.

    Handles the session-level tracing context and span management.
    A session IS a root span - all operations within the session are automatically
    tracked as child spans.
    """

    @property
    def session_id(self) -> str:
        return str(self.session.session_id)

    def __init__(self, session: Session):
        self.session = session
        self._is_ended = False
        self._shutdown_lock = threading.Lock()

        # Use global provider
        provider = get_tracer_provider()

        # Set up processor and exporter
        processor = SimpleSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces"))
        provider.add_span_processor(processor)

        # Initialize tracer and root span
        self.tracer = provider.get_tracer("agentops.session")
        session.span = self.tracer.start_span(
            "session.lifecycle", 
            attributes={
                "session.id": self.session_id, 
                "session.type": "root"
            }
        )
        
        # Create and activate the session context immediately
        self._context = trace.set_span_in_context(session.span)
        self._token = context.attach(self._context)

        # Store for cleanup
        _session_tracers[self.session_id] = self
        atexit.register(self.shutdown)

        logger.debug(f"[{self.session_id}] Session tracer initialized")

    def shutdown(self) -> None:
        """Shutdown and cleanup resources."""
        with self._shutdown_lock:
            if self._is_ended:
                return

            logger.debug(f"[{self.session_id}] Shutting down session tracer")

            # Detach our context if it's still active
            if self._token is not None:
                context.detach(self._token)
                self._token = None

            if self.session.span:
                self.session.span.end()

            provider = trace.get_tracer_provider()
            if isinstance(provider, TracerProvider):
                try:
                    provider.force_flush()
                except Exception as e:
                    logger.debug(f"[{self.session_id}] Error during flush: {e}")

            self._is_ended = True
            logger.debug(f"[{self.session_id}] Session tracer shutdown complete")

    def __del__(self):
        """Ensure cleanup on garbage collection."""
        self.shutdown()
