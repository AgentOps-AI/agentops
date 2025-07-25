"""Swarm Instrumentor for AutoGen

This module provides instrumentation specifically for Swarm.
"""

import logging
from typing import List

from opentelemetry.trace import SpanKind

from agentops.instrumentation.common import SpanAttributeManager
from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.span_kinds import AgentOpsSpanKindValues

from ..utils.common import AutoGenSpanManager


logger = logging.getLogger(__name__)


class SwarmInstrumentor:
    """Instrumentor for Swarm operations."""

    def __init__(self, tracer, attribute_manager: SpanAttributeManager):
        self.tracer = tracer
        self.attribute_manager = attribute_manager
        self.span_manager = AutoGenSpanManager(tracer, attribute_manager)


    def get_wrappers(self):
        """Return wrapper descriptors to patch AutoGen Swarm team.

        Format: (module_path, class_name, method_name, wrapper_factory)
        """

        module_path = "autogen_agentchat.teams._group_chat._swarm_group_chat"

        return [
            (
                module_path,
                "Swarm",
                "__init__",
                lambda: self._init_wrapper(),
            ),
        ]

    def _init_wrapper(self):
        """Wrap ``Swarm.__init__`` to create a top-level *workflow* span.

        We treat construction of a Swarm team as the beginning of a workflow.  This span
        is **synchronous** – it starts before the team is initialised and ends right after.
        """

        def wrapper(wrapped, instance, args, kwargs):
            # Extract participant names (best-effort).
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

            # Build span name – e.g., "swarm.Alice,Bob.workflow"
            names_fragment = ",".join(participant_names) if participant_names else "swarm"
            span_name = f"{names_fragment}.workflow"

            with self.tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT) as span:
                # Standard attributes
                span.set_attribute("gen_ai.system", "autogen")
                span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.WORKFLOW.value)
                span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "workflow")

                if participant_names:
                    span.set_attribute("autogen.participants", ", ".join(participant_names))

                # Delegate to original __init__
                return wrapped(*args, **kwargs)

        return wrapper 