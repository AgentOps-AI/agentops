"""Session tracing module for AgentOps.

This module provides automatic tracing capabilities for AgentOps sessions.
Each session represents a root span, with all operations within the session
tracked as child spans.
"""

from __future__ import annotations

import atexit
import threading
from typing import TYPE_CHECKING, Dict, Optional, Protocol
from uuid import uuid4
from weakref import WeakValueDictionary

from opentelemetry import context, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as gOTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.trace import NonRecordingSpan, Span, SpanContext, TraceFlags

from agentops.logging import logger
from agentops.session.base import SessionBase
from agentops.session.helpers import dict_to_span_attributes

if TYPE_CHECKING:
    from agentops.session.mixin.telemetry import TracedSession
    from agentops.session.session import Session

# Dictionary to store active session tracers
_session_tracers = WeakValueDictionary()

# Global TracerProvider instance
_tracer_provider: Optional[TracerProvider] = None


def get_tracer_provider() -> TracerProvider:
    """Get or create the global TracerProvider."""
    global _tracer_provider
    if _tracer_provider is None:
        _tracer_provider = TracerProvider(resource=Resource({SERVICE_NAME: "agentops"}))
        trace.set_tracer_provider(_tracer_provider)
    return _tracer_provider


def default_processor_cls():
    return BatchSpanProcessor


def get_session_tracer(session_id: str) -> Optional[SessionTracer]:
    """Get tracer for a session."""
    return _session_tracers.get(str(session_id))


class SessionTracer:
    """Core session tracing functionality.

    Handles the session-level tracing context and span management.
    A session IS a root span - all operations within the session are automatically
    tracked as child spans.
    """

    session: TracedSession

    @property
    def session_id(self) -> str:
        return str(self.session.session_id)

    def __init__(self, session: TracedSession):
        self.session = session
        self._is_ended = False
        self._shutdown_lock = threading.Lock()
        self._token = None
        self._context = None

        # Use global provider
        self.provider = provider = get_tracer_provider()

        ProcessorClass = default_processor_cls()
        # Set up processor and exporter
        if session.config.processor is not None:
            # Use the custom processor if provided
            provider.add_span_processor(session.config.processor)
        elif session.config.exporter is not None:
            # Use the custom exporter with the default processor class
            processor = ProcessorClass(
                session.config.exporter,
                max_queue_size=self.session.config.max_queue_size,
                export_timeout_millis=self.session.config.max_wait_time,
            )
            provider.add_span_processor(processor)
        else:
            # Use default processor and exporter
            endpoint = (
                session.config.exporter_endpoint
                if session.config.exporter_endpoint
                else "https://otlp.agentops.cloud/v1/traces"
            )
            processor = ProcessorClass(
                OTLPSpanExporter(endpoint=endpoint),
                max_queue_size=self.session.config.max_queue_size,
                export_timeout_millis=self.session.config.max_wait_time,
            )
            provider.add_span_processor(processor)

    def start(self):
        # Initialize tracer
        self.tracer = self.provider.get_tracer("agentops.session")

        # Create attributes from session data
        attributes = dict_to_span_attributes(self.session.dict())

        # We need to get a proper context for the tracer to use
        current_context = context.get_current()

        # Create a new recording span directly
        span = self.tracer.start_span("session", attributes=attributes)

        # Manually override the trace_id and span_id inside the span to match our session_id
        # Convert UUID to int by removing hyphens and converting hex to int
        # session_uuid_hex = str(self.session.session_id).replace("-", "")
        # trace_id = int(session_uuid_hex, 16)
        # span_id = trace_id & 0xFFFFFFFFFFFFFFFF  # Use lower 64 bits for span ID
        #
        # # Set the span's context to use our trace ID
        # # This is a bit of a hack, but it ensures the trace ID matches our session ID
        # span_context = span.get_span_context()
        # new_context = SpanContext(
        #     trace_id=trace_id,
        #     span_id=span_id,
        #     is_remote=False,
        #     trace_flags=TraceFlags(TraceFlags.SAMPLED),
        #     trace_state=span_context.trace_state if hasattr(span_context, "trace_state") else None,
        # )

        # Replace the span's context with our custom context
        # span._context = new_context  # type: ignore

        # Store the span in the session
        self.session._span = span

        # Activate the context
        self._context = trace.set_span_in_context(span)
        self._token = context.attach(self._context)

        # Store for cleanup
        _session_tracers[self.session_id] = self

        logger.debug(
            f"[{self.session_id}] Session tracer initialized with recording span: {type(self.session.span).__name__}"
        )

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

            # End the span if it exists and hasn't been ended yet
            if self.session.span is not None:
                # Check if the span has already been ended
                has_ended = hasattr(self.session.span, "end_time") and self.session.span.end_time is not None
                if not has_ended:
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
        # No need to manually remove from _session_tracers as WeakValueDictionary handles this automatically
