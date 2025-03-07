"""AgentOps semantic conventions for spans."""

from .span_kinds import SpanKind
from .core import CoreAttributes
from .agent import AgentAttributes
from .tool import ToolAttributes
from .llm import LLMAttributes
from .workflow import WorkflowAttributes
from .status import Status, AgentStatus, ToolStatus

# For backward compatibility and convenience
AgentOpsSpanAttributes = {
    "core": CoreAttributes,
    "agent": AgentAttributes,
    "tool": ToolAttributes,
    "llm": LLMAttributes,
    "workflow": WorkflowAttributes,
}

__all__ = [
    "SpanKind",
    "CoreAttributes",
    "AgentAttributes",
    "ToolAttributes",
    "LLMAttributes",
    "WorkflowAttributes",
    "Status",
    "AgentStatus",
    "ToolStatus",
    "AgentOpsSpanAttributes",
]
