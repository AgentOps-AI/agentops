"""SelectorGroupChat Instrumentor for AutoGen

This module provides instrumentation specifically for SelectorGroupChat.
"""

import logging

from opentelemetry.trace import SpanKind

from agentops.instrumentation.common import SpanAttributeManager
from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.span_kinds import AgentOpsSpanKindValues

from ..utils.common import AutoGenSpanManager


logger = logging.getLogger(__name__)


class SelectorGroupChatInstrumentor:
    """Instrumentor for SelectorGroupChat operations."""

    def __init__(self, tracer, attribute_manager: SpanAttributeManager):
        self.tracer = tracer
        self.attribute_manager = attribute_manager
        self.span_manager = AutoGenSpanManager(tracer, attribute_manager)

    def get_wrappers(self):
        """Return wrapper descriptors for AutoGen `SelectorGroupChat`.

        Each descriptor is a 4-tuple:
            (module_path, class_name, method_name, wrapper_factory)
        """

        module_path = "autogen_agentchat.teams._group_chat._selector_group_chat"

        return [
            (
                module_path,
                "SelectorGroupChat",
                "__init__",
                lambda: self._init_wrapper(),
            ),
        ]

    def _init_wrapper(self):
        """Wrap `SelectorGroupChat.__init__` with a synchronous workflow span."""

        def wrapper(wrapped, instance, args, kwargs):
            # Attempt to extract participants list from positional / keyword args
            participants = []
            if len(args) > 0 and isinstance(args[0], list):
                participants = args[0]
            elif "participants" in kwargs and isinstance(kwargs["participants"], list):
                participants = kwargs["participants"]

            participant_names = []
            try:
                participant_names = [p.name for p in participants if hasattr(p, "name")]
            except Exception:
                pass

            names_fragment = ",".join(participant_names) if participant_names else "selector"
            span_name = f"{names_fragment}.workflow"

            with self.tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT) as span:
                span.set_attribute("gen_ai.system", "autogen")
                span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.WORKFLOW.value)
                span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "workflow")

                if participant_names:
                    span.set_attribute("autogen.participants", ", ".join(participant_names))

                # Continue with original constructor
                return wrapped(*args, **kwargs)

        return wrapper
