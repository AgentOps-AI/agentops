from __future__ import annotations

import json
import logging
import sys
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, Union
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

from agentops.config import TESTING, Configuration
from agentops.helpers import get_ISO_time, safe_serialize
from agentops.http_client import HttpClient
from agentops.log_config import logger
from agentops.session.encoders import EventToSpanEncoder
from agentops.session.exporters import EventExporter, SessionLogExporter
from agentops.session.signals import (
    event_recorded,
    session_ended,
    session_initialized,
    session_started,
    session_updated,
)

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

The module uses a session-specific TracerProvider architecture where each session gets its own:
- TracerProvider: For session-specific resource attribution and sampling
- Tracer: For creating spans within the session's context
- SpanProcessor: For independent export pipeline configuration

This architecture enables:
- Complete isolation between concurrent sessions
- Independent lifecycle management
- Session-specific export configurations
- Easier debugging and monitoring per session

The module provides functions to:
- Set up logging telemetry components for a new session
- Clean up telemetry components when a session ends
"""


"""

1 Processor x Session
1 Exporter x Processor x Session
1 Global TracerProvider

"""

# Keep one global provider
_tracer_provider: Optional[TracerProvider] = None
_tracer: Optional[trace.Tracer] = None

# Keep session-specific processors
_session_processors: Dict[UUID, SpanProcessor] = {}


def _setup_trace_provider(config: Configuration) -> Tuple[TracerProvider, trace.Tracer]:
    """Set up global trace provider for the process.

    Creates a process-wide TracerProvider and Tracer. This ensures all telemetry
    data is properly attributed and managed through a single provider.

    Args:
        config: Configuration instance with telemetry settings

    Returns:
        Tuple containing:
        - TracerProvider: Global provider instance
        - Tracer: Global tracer for creating spans
    """
    resource = Resource.create({SERVICE_NAME: "agentops"})
    provider = TracerProvider(resource=resource)
    tracer = provider.get_tracer("agentops")
    return provider, tracer


def _setup_span_processor(config: Configuration, session) -> SpanProcessor:
    """Set up span processor for a specific session.

    Creates a session-specific SpanProcessor that handles the export pipeline.

    Args:
        config: Configuration instance with telemetry settings
        session: Session instance this processor belongs to

    Returns:
        SpanProcessor: Session-specific processor instance
    """
    # Set up exporter with session context
    exporter = EventExporter(session=session)

    # Get appropriate processor class

    processor = get_processor_cls()(
        span_exporter=exporter,
        schedule_delay_millis=config.max_wait_time,
        max_queue_size=config.max_queue_size,
        max_export_batch_size=min(
            max(config.max_queue_size // 20, 1),
            min(config.max_queue_size, 32),
        ),
    )

    _session_processors[session.session_id] = processor
    _tracer_provider.add_span_processor(processor)
    return processor


def initialize_tracer(config: Optional[Configuration] = None) -> None:
    """Initialize the global tracer if not already initialized.

    Args:
        config: Optional configuration instance with telemetry settings
    """
    global _tracer_provider, _tracer

    if _tracer is None:
        if config is None:
            config = Configuration()

        # Set up global provider and tracer
        _tracer_provider, _tracer = _setup_trace_provider(config)


def get_tracer() -> Optional[trace.Tracer]:
    """Get the global tracer instance.

    Returns:
        The global tracer instance or None if not initialized
    """
    return _tracer


def get_processor_cls():
    return BatchSpanProcessor


def _on_session_initialized(sender, **kwargs):
    """Initialize session-specific span processor when session is initialized"""
    if not _tracer_provider:
        initialize_tracer(sender.config)

    # Set up processor with session context
    processor = _setup_span_processor(sender.config, sender)


def _on_session_ended(sender, **kwargs):
    """Clean up session-specific span processor when session ends"""
    session_id = sender.session_id
    if processor := _session_processors.pop(session_id, None):
        try:
            if _tracer_provider:
                _tracer_provider.remove_span_processor(processor)
            processor.force_flush(timeout_millis=5000)
            processor.shutdown()
        except Exception as e:
            logger.warning(f"Error during processor cleanup: {e}")


def flush_session_telemetry(session_id: UUID) -> bool:
    """Force flush any pending telemetry data for a session.

    Args:
        session_id: The UUID of the session to flush

    Returns:
        bool: True if flush was successful, False if components not found
    """
    if processor := _session_processors.get(session_id):
        processor.force_flush()
        return True
    return False


# Initialize global tracer
initialize_tracer()
