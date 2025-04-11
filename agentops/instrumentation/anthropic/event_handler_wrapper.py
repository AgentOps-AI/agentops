"""Event handler wrapper for Anthropic's streaming API.

This module provides a wrapper for Anthropic's event handlers to
track events and metrics during streaming.
"""

import logging
from typing import Any, Dict, Optional

from opentelemetry.trace import Span
from agentops.semconv import CoreAttributes

logger = logging.getLogger(__name__)

class EventHandler:
    """Base EventHandler for Anthropic streams.
    
    This is used as a fallback if anthropic.EventHandler is not available.
    """
    def on_event(self, event: Dict[str, Any]) -> None:
        """Handle any event."""
        pass
    
    def on_text_delta(self, delta: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
        """Handle a text delta event."""
        pass
    
    def on_content_block_start(self, content_block_start: Dict[str, Any]) -> None:
        """Handle a content block start event."""
        pass
    
    def on_content_block_delta(self, delta: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
        """Handle a content block delta event."""
        pass
    
    def on_content_block_stop(self, content_block_stop: Dict[str, Any]) -> None:
        """Handle a content block stop event."""
        pass
    
    def on_message_start(self, message_start: Dict[str, Any]) -> None:
        """Handle a message start event."""
        pass
    
    def on_message_delta(self, delta: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
        """Handle a message delta event."""
        pass
    
    def on_message_stop(self, message_stop: Dict[str, Any]) -> None:
        """Handle a message stop event."""
        pass
    
    def on_error(self, error: Exception) -> None:
        """Handle an error event."""
        pass


class EventHandleWrapper:
    """Wrapper for Anthropic's EventHandler.
    
    This wrapper forwards all events to the original handler while also
    capturing metrics and adding them to the provided span.
    """
    
    def __init__(self, original_handler: Optional[EventHandler], span: Span):
        """Initialize the wrapper with the original handler and a span.
        
        Args:
            original_handler: The original Anthropic event handler (or None)
            span: The OpenTelemetry span to record metrics to
        """
        self._original_handler = original_handler
        self._span = span
        self._current_text_index = 0
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._text_accumulator = ""
    
    def on_event(self, event: Dict[str, Any]) -> None:
        """Handle any event by forwarding it to the original handler.
        
        Args:
            event: The event data
        """
        try:
            if self._original_handler is not None and hasattr(self._original_handler, "on_event"):
                self._original_handler.on_event(event)
        except Exception as e:
            logger.debug(f"Error in event handler on_event: {e}")
    
    def on_text_delta(self, delta: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
        """Handle a text delta event.
        
        Args:
            delta: The delta data
            snapshot: The current snapshot
        """
        try:
            if self._original_handler is not None and hasattr(self._original_handler, "on_text_delta"):
                self._original_handler.on_text_delta(delta, snapshot)
        except Exception as e:
            logger.debug(f"Error in event handler on_text_delta: {e}")
    
    def on_content_block_start(self, content_block_start: Dict[str, Any]) -> None:
        """Handle a content block start event.
        
        Args:
            content_block_start: The content block start data
        """
        try:
            if self._original_handler is not None and hasattr(self._original_handler, "on_content_block_start"):
                self._original_handler.on_content_block_start(content_block_start)
        except Exception as e:
            logger.debug(f"Error in event handler on_content_block_start: {e}")
    
    def on_content_block_delta(self, delta: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
        """Handle a content block delta event.
        
        Args:
            delta: The delta data
            snapshot: The current snapshot
        """
        try:
            if self._original_handler is not None and hasattr(self._original_handler, "on_content_block_delta"):
                self._original_handler.on_content_block_delta(delta, snapshot)
        except Exception as e:
            logger.debug(f"Error in event handler on_content_block_delta: {e}")
    
    def on_content_block_stop(self, content_block_stop: Dict[str, Any]) -> None:
        """Handle a content block stop event.
        
        Args:
            content_block_stop: The content block stop data
        """
        try:
            if self._original_handler is not None and hasattr(self._original_handler, "on_content_block_stop"):
                self._original_handler.on_content_block_stop(content_block_stop)
        except Exception as e:
            logger.debug(f"Error in event handler on_content_block_stop: {e}")
    
    def on_message_start(self, message_start: Dict[str, Any]) -> None:
        """Handle a message start event.
        
        Args:
            message_start: The message start data
        """
        try:
            if self._original_handler is not None and hasattr(self._original_handler, "on_message_start"):
                self._original_handler.on_message_start(message_start)
        except Exception as e:
            logger.debug(f"Error in event handler on_message_start: {e}")
    
    def on_message_delta(self, delta: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
        """Handle a message delta event.
        
        Args:
            delta: The delta data
            snapshot: The current snapshot
        """
        try:
            if self._original_handler is not None and hasattr(self._original_handler, "on_message_delta"):
                self._original_handler.on_message_delta(delta, snapshot)
        except Exception as e:
            logger.debug(f"Error in event handler on_message_delta: {e}")
    
    def on_message_stop(self, message_stop: Dict[str, Any]) -> None:
        """Handle a message stop event.
        
        Args:
            message_stop: The message stop data
        """
        try:
            if self._original_handler is not None and hasattr(self._original_handler, "on_message_stop"):
                self._original_handler.on_message_stop(message_stop)
        except Exception as e:
            logger.debug(f"Error in event handler on_message_stop: {e}")
    
    def on_error(self, error: Exception) -> None:
        """Handle an error event.
        
        Args:
            error: The error that occurred
        """
        try:
            self._span.record_exception(error)
            self._span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(error))
            self._span.set_attribute(CoreAttributes.ERROR_TYPE, error.__class__.__name__)
            
            if self._original_handler is not None and hasattr(self._original_handler, "on_error"):
                self._original_handler.on_error(error)
        except Exception as e:
            logger.debug(f"Error in event handler on_error: {e}") 