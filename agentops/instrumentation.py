from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Dict, List, Optional, Union
from uuid import UUID, uuid4

from opentelemetry import trace
from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, Sampler, TraceIdRatioBased
from termcolor import colored

from agentops.config import Configuration
from agentops.helpers import get_ISO_time, safe_serialize
from agentops.http_client import HttpClient
from agentops.log_config import logger
from agentops.session.encoders import EventToSpanEncoder
from agentops.session.exporters import EventExporter, SessionLogExporter
from agentops.session.signals import event_recorded, session_ended, session_started, session_updated

if TYPE_CHECKING:
    from agentops.client import Client
    from agentops.event import ErrorEvent, Event, EventType
    from agentops.session.session import Session

"""
This module handles OpenTelemetry instrumentation setup for AgentOps sessions.

Each AgentOps session requires its own telemetry setup to:
1. Track session-specific logs
2. Export logs to the AgentOps backend
3. Maintain isolation between different sessions running concurrently

The module provides functions to:
- Set up logging telemetry components for a new session
- Clean up telemetry components when a session ends
"""

# Map of session_id to LoggingHandler
_session_handlers: Dict[UUID, LoggingHandler] = {}


def get_session_handler(session_id: UUID) -> Optional[LoggingHandler]:
    """Get the logging handler for a specific session.

    Args:
        session_id: The UUID of the session

    Returns:
        The session's LoggingHandler if it exists, None otherwise
    """
    return _session_handlers.get(session_id)


def set_session_handler(session_id: UUID, handler: Optional[LoggingHandler]) -> None:
    """Set or remove the logging handler for a session.

    Args:
        session_id: The UUID of the session
        handler: The handler to set, or None to remove
    """
    if handler is None:
        _session_handlers.pop(session_id, None)
    else:
        _session_handlers[session_id] = handler


def setup_session_telemetry(session_id: UUID, log_exporter) -> tuple[LoggingHandler, BatchLogRecordProcessor]:
    """Set up OpenTelemetry logging components for a new session.

    Args:
        session_id: UUID identifier for the session, used to tag telemetry data
        log_exporter: SessionLogExporter instance that handles sending logs to AgentOps backend

    Returns:
        Tuple containing:
        - LoggingHandler: Handler that should be added to the logger
        - BatchLogRecordProcessor: Processor that batches and exports logs
    """
    # Create logging components
    resource = Resource.create({SERVICE_NAME: f"agentops.session.{str(session_id)}"})
    logger_provider = LoggerProvider(resource=resource)

    # Create processor and handler
    log_processor = BatchLogRecordProcessor(log_exporter)
    logger_provider.add_log_record_processor(log_processor)

    log_handler = LoggingHandler(
        level=logging.INFO,
        logger_provider=logger_provider,
    )

    # Register handler with session
    set_session_handler(session_id, log_handler)

    # Register signal handlers
    session_started.connect(_on_session_start)
    session_ended.connect(_on_session_end)
    event_recorded.connect(_on_session_event_recorded)

    return log_handler, log_processor


def cleanup_session_telemetry(log_handler: LoggingHandler, log_processor: BatchLogRecordProcessor) -> None:
    """Clean up OpenTelemetry logging components when a session ends.

    This function ensures proper cleanup by:
    1. Removing the handler from the logger
    2. Closing the handler to free resources
    3. Flushing any pending logs in the processor
    4. Shutting down the processor
    5. Disconnecting signal handlers

    Args:
        log_handler: The session's LoggingHandler to be removed and closed
        log_processor: The session's BatchLogRecordProcessor to be flushed and shutdown
    """
    from agentops.log_config import logger

    try:
        # Remove and close handler
        logger.removeHandler(log_handler)
        log_handler.close()

        # Remove from session handlers
        for session_id, handler in list(_session_handlers.items()):
            if handler is log_handler:
                set_session_handler(session_id, None)
                break

        # Shutdown processor
        log_processor.force_flush(timeout_millis=5000)
        log_processor.shutdown()
    except Exception as e:
        logger.warning(f"Error during logging cleanup: {e}")


class SessionTracer:
    """Manages OpenTelemetry tracing for a session"""

    @classmethod
    def exporter_cls(cls) -> type[BatchSpanProcessor] | type[SimpleSpanProcessor]:
        """
        Return the exporter class to use for the session.
        The reason we use this class is for ease of mocking in tests.
        """
        return BatchSpanProcessor

    def __init__(self, session_id: UUID, config: Configuration):
        # Create session-specific resource and tracer
        resource = Resource.create({SERVICE_NAME: f"agentops.session.{str(session_id)}", "session.id": str(session_id)})
        self.tracer_provider = TracerProvider(resource=resource)
        self.tracer = self.tracer_provider.get_tracer(f"agentops.session.{str(session_id)}")

        from agentops.session.registry import get_session_by_id

        # Set up exporter
        self.exporter = EventExporter(session=get_session_by_id(session_id))

        processor_cls = self.exporter_cls()
        if processor_cls == SimpleSpanProcessor:
            self.span_processor = processor_cls(self.exporter)
        else:
            self.span_processor = processor_cls(
                self.exporter,
                max_queue_size=config.max_queue_size,
                schedule_delay_millis=config.max_wait_time,
                max_export_batch_size=min(
                    max(config.max_queue_size // 20, 1),
                    min(config.max_queue_size, 32),
                ),
                export_timeout_millis=20000,
            )
        self.tracer_provider.add_span_processor(self.span_processor)

    def cleanup(self):
        """Clean up tracer resources"""
        if hasattr(self, "span_processor"):
            try:
                self.span_processor.force_flush(timeout_millis=5000)
                self.span_processor.shutdown()
            except Exception as e:
                logger.warning(f"Error during span processor cleanup: {e}")

        if hasattr(self, "exporter"):
            try:
                self.exporter.shutdown()
            except Exception as e:
                logger.warning(f"Error during exporter cleanup: {e}")


def _on_session_start(sender):
    """Initialize session tracer when session starts"""
    # Initialize tracer when session starts - this is the proper time
    tracer = SessionTracer(sender.session_id, sender.config)
    sender._tracer = tracer

    # Record session start span
    with tracer.tracer.start_as_current_span(
        name="session.start",
        attributes={
            "session.id": str(sender.session_id),
            "session.tags": ",".join(sender.tags) if sender.tags else "",
            "session.init_timestamp": sender.init_timestamp,
        },
    ) as span:
        span.set_attribute("session.start", True)


def _on_session_end(sender, end_state: str, end_state_reason: Optional[str]):
    """Clean up tracer when session ends"""
    # By this point tracer should exist since session was started
    with sender._tracer.tracer.start_as_current_span(
        name="session.end",
        attributes={
            "session.id": str(sender.session_id),
            "session.end_state": end_state,
            "session.end_state_reason": end_state_reason or "",
            "session.end_timestamp": sender.end_timestamp or get_ISO_time(),
        },
    ) as span:
        span.set_attribute("session.end", True)

    sender._tracer.cleanup()


def _on_session_event_recorded(sender: Session, event: Event, flush_now=False, **kwargs):
    """Handle completion of event recording for telemetry"""
    logger.debug(f"Finished recording event: {event}")

    # Create spans from definitions
    span_definitions = EventToSpanEncoder.encode(event)

    # Create spans
    for span_def in span_definitions:
        with sender._tracer.tracer.start_as_current_span(
            name=span_def.name,
            kind=span_def.kind,
            attributes=span_def.attributes,
        ) as span:
            # Set event end timestamp when span ends
            event.end_timestamp = get_ISO_time()

            # Update event counts if applicable
            event_type = span_def.attributes.get("event_type")
            if event_type in sender.event_counts:
                sender.event_counts[event_type] += 1

    # Handle manual flush if requested
    if flush_now:
        sender._tracer.span_processor.force_flush()


def register_handlers():
    """Register signal handlers"""
    # Disconnect signal handlers to ensure clean state
    unregister_handlers()
    import agentops.event  # Ensure event.py handlers are registered before instrumentation.py handlers

    session_started.connect(_on_session_start)
    session_ended.connect(_on_session_end)
    event_recorded.connect(_on_session_event_recorded)


def unregister_handlers():
    """Unregister signal handlers"""
    session_started.disconnect(_on_session_start)
    session_ended.disconnect(_on_session_end)
    event_recorded.disconnect(_on_session_event_recorded)


register_handlers()
