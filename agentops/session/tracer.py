"""Session tracing module for AgentOps.

This module provides automatic tracing capabilities for AgentOps sessions.
Each session represents a root span, with all operations within the session
tracked as child spans.
"""

from __future__ import annotations

import atexit
import threading
from typing import TYPE_CHECKING, Optional
from weakref import WeakValueDictionary

from opentelemetry import context, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
    OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

from agentops.logging import logger
from agentops.session.signals import (session_ended, session_initialized,
                                      session_started)
from agentops.session.helpers import dict_to_span_attributes

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


@session_initialized.connect
def setup_session_tracer(sender: Session, **kwargs):
    """When session initializes, create telemetry with non-recording span"""
    try:
        # SessionTelemetry will check the session.config for custom exporter/processor settings
        setattr(sender, "telemetry", SessionTelemetry(sender))
        logger.debug(f"[{sender.session_id}] Session telemetry initialized with non-recording span")
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


@session_started.connect
def start_recording_session_span(sender: Session, **kwargs):
    """Start recording the session span when session is actually started"""
    try:
        if hasattr(sender, "telemetry"):
            sender.telemetry.start_recording_span()
            # Add verification that the span was actually replaced
            if isinstance(sender.span, NonRecordingSpan):
                logger.error(f"[{sender.session_id}] Failed to replace NonRecordingSpan with recording span")
            else:
                logger.debug(f"[{sender.session_id}] Session span started recording successfully")
    except Exception as e:
        logger.error(f"[{sender.session_id}] Failed to start recording session span: {e}")
        import traceback

        logger.error(traceback.format_exc())


def default_processor_cls():
    return SimpleSpanProcessor


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
        self._token = None
        self._context = None
        self._recording_span = None  # Initialize the recording span attribute

        # Use global provider
        provider = get_tracer_provider()

        ProcessorClass = default_processor_cls()
        # Set up processor and exporter
        if session.config.processor is not None:
            # Use the custom processor if provided
            provider.add_span_processor(session.config.processor)
            logger.debug(f"[{self.session_id}] Using custom span processor")
        elif session.config.exporter is not None:
            # Use the custom exporter with a SimpleSpanProcessor if only exporter is provided
            processor = ProcessorClass(session.config.exporter)
            provider.add_span_processor(processor)
            logger.debug(f"[{self.session_id}] Using custom span exporter with SimpleSpanProcessor")
        else:
            # Use default processor and exporter
            processor = ProcessorClass(OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces"))
            provider.add_span_processor(processor)
            logger.debug(f"[{self.session_id}] Using default span processor and exporter")

        # Initialize tracer
        self.tracer = provider.get_tracer("agentops.session")

        # Create a non-recording span context
        span_context = SpanContext(
            trace_id=int(self.session_id.replace("-", "")[:16], 16),  # Use part of session_id as trace_id
            span_id=int(self.session_id.replace("-", "")[-16:], 16),  # Use part of session_id as span_id
            is_remote=False,
            trace_flags=TraceFlags(0),  # 0 means not sampled (non-recording)
        )

        # Create a non-recording span and assign it to session.span
        self.session.span = NonRecordingSpan(span_context)

        # Store for cleanup
        _session_tracers[self.session_id] = self
        atexit.register(self.shutdown)

        logger.debug(f"[{self.session_id}] Session tracer initialized with non-recording span")

    def start_recording_span(self):
        """Start a recording span when the session actually starts"""
        # Add more detailed logging
        logger.debug(f"[{self.session_id}] Attempting to start recording span")

        if self._recording_span is not None:
            logger.debug(f"[{self.session_id}] Recording span already started")
            return

        try:
            # Create a real recording span with the same context as the non-recording one
            attributes = dict_to_span_attributes(self.session.dict())

            # Make sure self.session.span is not None before using it
            if self.session.span is None:
                logger.error(f"[{self.session_id}] Session span is None, cannot start recording")
                return

            # Get the span context from the non-recording span
            span_context = self.session.span.get_span_context()

            # Create the recording span using the context from the non-recording span
            self._recording_span = self.tracer.start_span("session", attributes=attributes)

            # Replace the non-recording span with the recording one
            self.session.span = self._recording_span

            # Create and activate the session context
            self._context = trace.set_span_in_context(self.session.span)
            self._token = context.attach(self._context)

            logger.debug(f"[{self.session_id}] Started recording session span: {type(self.session.span).__name__}")
        except Exception as e:
            logger.error(f"[{self.session_id}] Error starting recording span: {e}")
            import traceback

            logger.error(traceback.format_exc())

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

            # End the span if it exists
            if self.session.span is not None:
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
