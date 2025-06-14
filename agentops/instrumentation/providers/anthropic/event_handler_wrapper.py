"""Event handler wrapper for Anthropic's streaming API.

This module provides a wrapper for Anthropic's event handlers to
track events and metrics during streaming.
"""

import logging
from typing import Any, Dict, Optional

from opentelemetry.trace import Span
from agentops.semconv import CoreAttributes

logger = logging.getLogger(__name__)


class EventHandleWrapper:
    """Wrapper for Anthropic's EventHandler.

    This wrapper forwards all events to the original handler while also
    capturing metrics and adding them to the provided span.
    """

    def __init__(self, original_handler: Optional[Any], span: Span):
        """Initialize the wrapper with the original handler and a span.

        Args:
            original_handler: The original Anthropic event handler (or None)
            span: The OpenTelemetry span to record metrics to
        """
        self._original_handler = original_handler
        self._span = span

    def _forward_event(self, method_name: str, *args, **kwargs) -> None:
        """Forward an event to the original handler if it exists.

        Args:
            method_name: Name of the method to call on the original handler
            *args: Positional arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method
        """
        try:
            if self._original_handler is not None and hasattr(self._original_handler, method_name):
                method = getattr(self._original_handler, method_name)
                method(*args, **kwargs)
        except Exception as e:
            logger.debug(f"Error in event handler {method_name}: {e}")

    def on_event(self, event: Dict[str, Any]) -> None:
        """Handle any event by forwarding it to the original handler."""
        self._forward_event("on_event", event)

    def on_text_delta(self, delta: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
        """Handle a text delta event."""
        self._forward_event("on_text_delta", delta, snapshot)

    def on_content_block_start(self, content_block_start: Dict[str, Any]) -> None:
        """Handle a content block start event."""
        self._forward_event("on_content_block_start", content_block_start)

    def on_content_block_delta(self, delta: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
        """Handle a content block delta event."""
        self._forward_event("on_content_block_delta", delta, snapshot)

    def on_content_block_stop(self, content_block_stop: Dict[str, Any]) -> None:
        """Handle a content block stop event."""
        self._forward_event("on_content_block_stop", content_block_stop)

    def on_message_start(self, message_start: Dict[str, Any]) -> None:
        """Handle a message start event."""
        self._forward_event("on_message_start", message_start)

    def on_message_delta(self, delta: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
        """Handle a message delta event."""
        self._forward_event("on_message_delta", delta, snapshot)

    def on_message_stop(self, message_stop: Dict[str, Any]) -> None:
        """Handle a message stop event."""
        self._forward_event("on_message_stop", message_stop)

    def on_error(self, error: Exception) -> None:
        """Handle an error event."""
        try:
            self._span.record_exception(error)
            self._span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(error))
            self._span.set_attribute(CoreAttributes.ERROR_TYPE, error.__class__.__name__)

            if self._original_handler is not None and hasattr(self._original_handler, "on_error"):
                self._original_handler.on_error(error)
        except Exception as e:
            logger.debug(f"Error in event handler on_error: {e}")
