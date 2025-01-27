from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, Sampler, TraceIdRatioBased

if TYPE_CHECKING:
    from opentelemetry.sdk._logs import LoggingHandler

    from agentops.client import Client


_log_handler = None


def set_log_handler(log_handler: Optional[LoggingHandler]) -> None:
    """Set the OTLP log handler.

    Args:
        log_handler: The logging handler to use for OTLP
    """
    _log_handler = log_handler


def get_log_handler() -> Optional[LoggingHandler]:
    """Get the current OTLP log handler.

    Returns:
        The current logging handler if set, None otherwise
    """
    return _log_handler


def add_telemetry_log_handler(logger: logging.Logger) -> None:
    """Add the OTLP log handler to the given logger if configured.

    Args:
        logger: The logger to add the handler to
    """
    global _log_handler
    if _log_handler:
        logger.addHandler(_log_handler)
