"""Session tracing module for AgentOps.

This module provides automatic tracing capabilities for AgentOps sessions.
Each session represents a root span, with all operations within the session
tracked as child spans.
"""

from __future__ import annotations

import atexit
import threading
import logging
from typing import TYPE_CHECKING, Dict, Optional, Protocol, Union, Any, Set
from uuid import uuid4
from weakref import WeakValueDictionary

from opentelemetry import context, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as gOTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanProcessor
from opentelemetry.trace import NonRecordingSpan, Span, SpanContext, TraceFlags, Status, StatusCode

from agentops.logging import logger
from agentops.session.base import SessionBase
from agentops.session.helpers import dict_to_span_attributes
from agentops.session.processors import InFlightSpanProcessor

if TYPE_CHECKING:
    from agentops.session.mixin.telemetry import TracedSession
    from agentops.session.session import Session

# Dictionary to store active session tracers
_session_tracers: WeakValueDictionary[str, "SessionTracer"] = WeakValueDictionary()

# Global TracerProvider instance
_tracer_provider: Optional[TracerProvider] = None

# Thread-local storage for tokens
_thread_local = threading.local()


def get_tracer_provider() -> TracerProvider:
    """Get or create the global TracerProvider."""
    global _tracer_provider
    if _tracer_provider is None:
        _tracer_provider = TracerProvider(resource=Resource({SERVICE_NAME: "agentops"}))
        trace.set_tracer_provider(_tracer_provider)
    return _tracer_provider


def get_session_tracer(session_id: str) -> Optional["SessionTracer"]:
    """Get tracer for a session."""
    return _session_tracers.get(str(session_id))


class SessionTracer:
    """Core session tracing functionality.

    Handles the session-level tracing context and span management.
    A session IS a root span - all operations within the session are automatically
    tracked as child spans.
    """

    session: "TracedSession"

    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return str(self.session.session_id)

    def __init__(self, session: "TracedSession"):
        """Initialize the session tracer.

        Args:
            session: The session to trace.
        """
        self.session = session
        self._is_ended = False
        self._shutdown_lock = threading.Lock()
        self._context = None
        self._span_processor = None

        # Initialize thread-local storage for this tracer
        if not hasattr(_thread_local, "tokens"):
            _thread_local.tokens = {}

        # Use global provider
        self.provider = provider = get_tracer_provider()

        # Set up processor and exporter
        if session.config.processor is not None:
            # Use the custom processor if provided
            self._span_processor = session.config.processor
            provider.add_span_processor(self._span_processor)
        elif session.config.exporter is not None:
            # Use the custom exporter with InFlightSpanProcessor
            self._span_processor = InFlightSpanProcessor(
                session.config.exporter,
                max_export_batch_size=session.config.max_queue_size,
                schedule_delay_millis=session.config.max_wait_time,
            )
            provider.add_span_processor(self._span_processor)
        else:
            # Use default processor and exporter
            endpoint = (
                session.config.exporter_endpoint
                if session.config.exporter_endpoint
                else "https://otlp.agentops.cloud/v1/traces"
            )
            self._span_processor = InFlightSpanProcessor(
                OTLPSpanExporter(endpoint=endpoint),
                max_export_batch_size=session.config.max_queue_size,
                schedule_delay_millis=session.config.max_wait_time,
            )
            provider.add_span_processor(self._span_processor)

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

        # Store the token in thread-local storage
        thread_id = threading.get_ident()
        token = context.attach(self._context)
        _thread_local.tokens[f"{self.session_id}_{thread_id}"] = token

        # Store for cleanup
        _session_tracers[self.session_id] = self

        logger.debug(
            f"[{self.session_id}] Session tracer initialized with recording span: {type(self.session._span).__name__}"
        )

    def _end_session_span(self) -> None:
        """End the session span if it exists and hasn't been ended yet."""
        # Use a more direct approach with proper error handling
        try:
            span = self.session._span
            if span is None:
                return

            # Try to end the span
            span.end()
            logger.debug(f"[{self.session_id}] Ended session span")
        except Exception as e:
            # Log any other errors but don't raise them
            logger.debug(f"[{self.session_id}] Note: {e}")

    def shutdown(self) -> None:
        """Shutdown and cleanup resources."""
        # Use a direct approach with the lock
        with self._shutdown_lock:
            # Early return if already ended
            if self._is_ended:
                return

            logger.debug(f"[{self.session_id}] Shutting down session tracer")

            # Clean up the context if it's active
            thread_id = threading.get_ident()
            token_key = f"{self.session_id}_{thread_id}"

            if hasattr(_thread_local, "tokens") and token_key in _thread_local.tokens:
                try:
                    context.detach(_thread_local.tokens[token_key])
                    del _thread_local.tokens[token_key]
                except ValueError as e:
                    # This can happen if we're in a different thread than the one that created the token
                    # It's safe to ignore this error as the context will be cleaned up when the thread exits
                    logger.debug(f"[{self.session_id}] Context token was created in a different thread: {e}")
                    if token_key in _thread_local.tokens:
                        del _thread_local.tokens[token_key]
                except Exception as e:
                    logger.debug(f"[{self.session_id}] Error detaching context: {e}")
            else:
                # This is a different thread than the one that created the token
                # We can't detach the token, but we can log a debug message
                logger.debug(f"[{self.session_id}] No context token found for thread {thread_id}")

            # End the session span if it exists and hasn't been ended yet
            try:
                if self.session._span is not None:
                    # Check if the span has already been ended
                    if self.session._span.end_time is None:  # type: ignore
                        self.session._span.end()
                        logger.debug(f"[{self.session_id}] Ended session span")
                    else:
                        logger.debug(f"[{self.session_id}] Session span already ended")
            except AttributeError:
                # Session might not have a span attribute
                pass
            except Exception as e:
                # Log any other errors but don't raise them
                logger.debug(f"[{self.session_id}] Note when ending span: {e}")

            # Flush the span processor if available
            if self._span_processor:
                try:
                    self._span_processor.force_flush()
                    logger.debug(f"[{self.session_id}] Flushed span processor")
                except Exception as e:
                    logger.warning(f"[{self.session_id}] Error flushing span processor: {e}")

            # Flush the tracer provider
            provider = trace.get_tracer_provider()
            if isinstance(provider, TracerProvider):
                try:
                    provider.force_flush()
                    logger.debug(f"[{self.session_id}] Flushed tracer provider")
                except Exception as e:
                    logger.debug(f"[{self.session_id}] Error during flush: {e}")

            # Mark as ended
            self._is_ended = True
            logger.debug(f"[{self.session_id}] Session tracer shutdown complete")

    def __del__(self):
        """Ensure cleanup on garbage collection."""
        try:
            self.shutdown()
        except Exception as e:
            logger.debug(f"Error during cleanup in __del__: {e}")
