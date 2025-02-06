from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from opentelemetry import trace
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, Sampler, TraceIdRatioBased

if TYPE_CHECKING:
    from agentops.client import Client

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


def setup_session_telemetry(session_id: str, log_exporter) -> tuple[LoggingHandler, BatchLogRecordProcessor]:
    """Set up OpenTelemetry logging components for a new session.

    This function creates the necessary components to capture and export logs for a specific session:
    - A LoggerProvider with session-specific resource attributes
    - A BatchLogRecordProcessor to batch and export logs
    - A LoggingHandler to capture logs and forward them to the processor

    Args:
        session_id: Unique identifier for the session, used to tag telemetry data
        log_exporter: SessionLogExporter instance that handles sending logs to AgentOps backend

    Returns:
        Tuple containing:
        - LoggingHandler: Handler that should be added to the logger
        - BatchLogRecordProcessor: Processor that batches and exports logs
    """
    # Create logging components
    resource = Resource.create({SERVICE_NAME: f"agentops.session.{session_id}"})
    logger_provider = LoggerProvider(resource=resource)

    # Create processor and handler
    log_processor = BatchLogRecordProcessor(log_exporter)
    logger_provider.add_log_record_processor(log_processor)  # Add processor to provider

    log_handler = LoggingHandler(
        level=logging.INFO,
        logger_provider=logger_provider,
    )

    # Register handler with session
    set_session_handler(session_id, log_handler)

    return log_handler, log_processor


def cleanup_session_telemetry(log_handler: LoggingHandler, log_processor: BatchLogRecordProcessor) -> None:
    """Clean up OpenTelemetry logging components when a session ends.

    This function ensures proper cleanup by:
    1. Removing the handler from the logger
    2. Closing the handler to free resources
    3. Flushing any pending logs in the processor
    4. Shutting down the processor

    Args:
        log_handler: The session's LoggingHandler to be removed and closed
        log_processor: The session's BatchLogRecordProcessor to be flushed and shutdown

    Used by:
        Session.end_session() to clean up logging components when the session ends
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
