"""AgentOps semantic conventions for spans."""

from agentops.semconv.span_kinds import SpanKind
from agentops.semconv.core import CoreAttributes
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.tool import ToolAttributes
from agentops.semconv.status import ToolStatus
from agentops.semconv.workflow import WorkflowAttributes
from agentops.semconv.instrumentation import InstrumentationAttributes
from agentops.semconv.enum import LLMRequestTypeValues
from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.meters import Meters
from agentops.semconv.span_kinds import AgentOpsSpanKindValues
from agentops.semconv.resource import ResourceAttributes
from agentops.semconv.message import MessageAttributes
from agentops.semconv.langchain import LangChainAttributes, LangChainAttributeValues

SUPPRESS_LANGUAGE_MODEL_INSTRUMENTATION_KEY = "suppress_language_model_instrumentation"
__all__ = [
    "SUPPRESS_LANGUAGE_MODEL_INSTRUMENTATION_KEY",
    "SpanKind",
    "CoreAttributes",
    "AgentAttributes",
    "ToolAttributes",
    "ToolStatus",
    "WorkflowAttributes",
    "InstrumentationAttributes",
    "LLMRequestTypeValues",
    "SpanAttributes",
    "Meters",
    "AgentOpsSpanKindValues",
    "ResourceAttributes",
    "MessageAttributes",
    "LangChainAttributes",
    "LangChainAttributeValues",
]
