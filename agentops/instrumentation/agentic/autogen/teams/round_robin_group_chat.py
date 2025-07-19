"""RoundRobinGroupChat Instrumentor for AutoGen

This module provides instrumentation specifically for RoundRobinGroupChat,
which handles round-robin multi-agent conversations.
"""

import logging
from typing import Dict, Any
from opentelemetry.trace import SpanKind, Status, StatusCode

from agentops.instrumentation.common import SpanAttributeManager, create_span
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.span_kinds import AgentOpsSpanKindValues
from ..utils.common import (
    AutoGenSpanManager,
    safe_str,
    safe_extract_content,
    instrument_coroutine,
    instrument_async_generator,
)
from inspect import iscoroutine
from opentelemetry.trace import set_span_in_context
from opentelemetry import context as context_api
logger = logging.getLogger(__name__)


class RoundRobinGroupChatInstrumentor:
    """Instrumentor for RoundRobinGroupChat operations."""
    
    def __init__(self, tracer, attribute_manager: SpanAttributeManager):
        self.tracer = tracer
        self.attribute_manager = attribute_manager
        self.span_manager = AutoGenSpanManager(tracer, attribute_manager)
    
    def get_wrappers(self):
        """Get list of methods to wrap for RoundRobinGroupChat and base group chat manager.

        Returns a list of tuples describing what to wrap.  The tuple structure is:
            (module_path, class_name, method_name, wrapper_factory)

        module_path   – fully-qualified python module that contains the class
        class_name    – the class that owns the method to wrap
        method_name   – the method on that class
        wrapper_factory – lambda returning the actual wrapper function
        """

        base_module = "autogen_agentchat.teams._group_chat._base_group_chat_manager"

        return [
            # Wrap the method that transitions control to the next agent(s).
            # This represents an *agent* level span because it orchestrates agent execution.
            (
                base_module,
                "BaseGroupChatManager",
                "_transition_to_next_speakers",
                lambda: self._transition_wrapper(),
            ),
        ]
        
    def _transition_wrapper(self):
        """Create a wrapper for `_transition_to_next_speakers` to emit an *agent* span."""



        def wrapper(wrapped, instance, args, kwargs):
            agent_name = getattr(instance, "_name", "group_chat")
            # Attempt to extract the current task / prompt text for naming
            task_text = None
            if args and isinstance(args[0], str):
                task_text = args[0].strip()

            if not task_text:
                task_text = getattr(instance, "_current_task", None)

            span_name_base = task_text if task_text else agent_name
            span_name = f"{span_name_base}.task" if not str(span_name_base).endswith(".task") else span_name_base

            # Start span manually so we can end it after async completes
            span = self.tracer.start_span(span_name)


            token = context_api.attach(set_span_in_context(span))

            # Set attributes immediately
            span.set_attribute("gen_ai.system", "autogen")
            span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, "workflow.step")
            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "task")

            if task_text:
                span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_INPUT, safe_str(task_text, 500))

            self.span_manager.set_base_attributes(span, agent_name, "task")

            result = wrapped(*args, **kwargs)

            if iscoroutine(result):

                async def instrumented():
                    try:
                        output = await result
                        # capture output
                        try:
                            content = safe_extract_content(output)
                            if content:
                                span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_OUTPUT, safe_str(content, 500))
                        except Exception:
                            pass
                        return output
                    finally:
                        span.end()
                        context_api.detach(token)

                return instrumented()

            # synchronous path
            try:
                content = safe_extract_content(result)
                if content:
                    span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_OUTPUT, safe_str(content, 500))
            except Exception:
                pass

            span.end()
            context_api.detach(token)

            return result
         
        return wrapper
