"""Common utilities for AutoGen instrumentation"""

import logging
from typing import Any, Dict, Optional, AsyncGenerator, Awaitable
from opentelemetry.trace import SpanKind, Status, StatusCode, Span
from opentelemetry.context import Context

from agentops.instrumentation.common import (
    SpanAttributeManager,
    create_span,
)
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.span_kinds import AgentOpsSpanKindValues

logger = logging.getLogger(__name__)


class AutoGenSpanManager:
    """Manages spans for AutoGen agent operations."""
    
    def __init__(self, tracer, attribute_manager: SpanAttributeManager):
        self.tracer = tracer
        self.attribute_manager = attribute_manager
    
    def create_agent_span(self, agent_name: str, operation: str = "agent"):
        """Create a span for an agent operation."""
        if not self.tracer:
            return None
            
        span_name = f"{operation}.{agent_name}.workflow"
        span_context = create_span(
            self.tracer, span_name, kind=SpanKind.CLIENT, attribute_manager=self.attribute_manager
        )
        return span_context
    
    def set_base_attributes(self, span: Span, agent_name: str, operation: str):
        """Set base attributes common to all AutoGen operations."""
        span.set_attribute("gen_ai.operation.name", operation)
        span.set_attribute("gen_ai.system", "autogen")
        span.set_attribute("gen_ai.agent.name", agent_name)
        span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
        span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")
        span.set_attribute(AgentAttributes.AGENT_NAME, agent_name)


def extract_agent_attributes(instance, args, kwargs) -> Dict[str, Any]:
    """Extract agent attributes from instance, args, and kwargs."""
    attributes = {}
    
    # Get name from kwargs or args (different signatures for different agents)
    name = kwargs.get("name") or (args[0] if args else "unnamed_agent")
    attributes["name"] = name
    
    # Determine agent type from class name
    agent_type = instance.__class__.__name__ if hasattr(instance, '__class__') else "Agent"
    attributes["type"] = agent_type
    
    # Get description from different possible sources
    description = (
        kwargs.get("description") or 
        kwargs.get("system_message") or
        (args[1] if len(args) > 1 else "")
    )
    if description:
        attributes["description"] = safe_str(description)
    
    return attributes


def safe_str(value: Any, max_length: Optional[int] = None) -> str:
    """Safely convert *value* to a string.
    
    """

    try:
        if value is None:
            return ""

        str_val = str(value)

        if max_length is not None and max_length > 0 and len(str_val) > max_length:
            return str_val[:max_length] + "..."

        return str_val
    except Exception:
        return "<unable to convert to string>"


def safe_extract_content(obj: Any, content_attr: str = "content") -> str:
    """Safely extract content from an object."""
    try:
        if hasattr(obj, content_attr):
            content = getattr(obj, content_attr)
            return safe_str(content)
        elif hasattr(obj, "__dict__"):
            # Try to extract from dict
            content = obj.__dict__.get(content_attr, "")
            return safe_str(content)
    except Exception as e:
        logger.debug(f"Error extracting content: {e}")
    return ""


def create_agent_span(tracer, agent_name: str, operation: str, attribute_manager: SpanAttributeManager):
    """Create a span for agent operations with standard attributes."""
    if not tracer:
        logger.debug("[AutoGen DEBUG] No tracer available, skipping span creation")
        return None
    
    span_name = f"{operation} {agent_name}.workflow"
    span_context = create_span(
        tracer, span_name, kind=SpanKind.CLIENT, attribute_manager=attribute_manager
    )
    return span_context


async def instrument_async_generator(generator: AsyncGenerator, span: Span, operation: str):
    """Instrument an async generator with span tracking."""
    item_count = 0
    event_types = set()
    total_tokens = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    try:
        async for item in generator:
            item_count += 1
            item_type = type(item).__name__
            event_types.add(item_type)
            
            # Track token usage if available
            if hasattr(item, 'usage') and item.usage:
                if hasattr(item.usage, 'prompt_tokens'):
                    total_prompt_tokens += item.usage.prompt_tokens or 0
                if hasattr(item.usage, 'completion_tokens'):
                    total_completion_tokens += item.usage.completion_tokens or 0
                if hasattr(item.usage, 'total_tokens'):
                    total_tokens += item.usage.total_tokens or 0
            
            yield item
            
    except Exception as e:
        logger.debug(f"[AutoGen DEBUG] Error in instrumented generator: {e}")
        span.set_status(Status(StatusCode.ERROR, str(e)))
        raise
    finally:
        # Set final span attributes
        span.set_attribute(f"gen_ai.{operation}.item_count", item_count)
        span.set_attribute(f"gen_ai.{operation}.event_types", ", ".join(event_types))
        
        if total_tokens > 0:
            span.set_attribute("gen_ai.usage.prompt_tokens", total_prompt_tokens)
            span.set_attribute("gen_ai.usage.completion_tokens", total_completion_tokens)
            span.set_attribute("gen_ai.usage.total_tokens", total_tokens)


async def instrument_coroutine(coro: Awaitable, span: Span, operation: str):
    """Instrument a coroutine with span tracking."""
    try:
        result = await coro
        
        # Track result attributes
        if hasattr(result, '__dict__'):
            
            
            if hasattr(result, 'chat_message'):
                content = safe_extract_content(result.chat_message)
                if content:
                    span.set_attribute(f"gen_ai.{operation}.response_content", safe_str(content, 500))
            
            # Track usage if available
            if hasattr(result, 'usage') and result.usage:
                if hasattr(result.usage, 'prompt_tokens'):
                    span.set_attribute("gen_ai.usage.prompt_tokens", result.usage.prompt_tokens or 0)
                if hasattr(result.usage, 'completion_tokens'):
                    span.set_attribute("gen_ai.usage.completion_tokens", result.usage.completion_tokens or 0)
                if hasattr(result.usage, 'total_tokens'):
                    span.set_attribute("gen_ai.usage.total_tokens", result.usage.total_tokens or 0)
        
        return result
        
    except Exception as e:
        logger.debug(f"[AutoGen DEBUG] Error in {operation}: {e}")
        span.set_status(Status(StatusCode.ERROR, str(e)))
        raise 