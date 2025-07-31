"""Span kinds for AgentOps."""

from enum import Enum


class AgentOpsSpanKindValues(Enum):
    """Standard span kind values for AgentOps."""

    WORKFLOW = "workflow"
    SESSION = "session"
    TASK = "task"
    OPERATION = "operation"
    AGENT = "agent"
    TOOL = "tool"
    LLM = "llm"
    CHAIN = "chain"
    TEXT = "text"
    GUARDRAIL = "guardrail"
    HTTP = "http"
    UNKNOWN = "unknown"


# Legacy SpanKind class for backward compatibility
class SpanKind:
    """Legacy span kind definitions - use AgentOpsSpanKindValues instead."""

    # Agent action kinds
    AGENT_ACTION = "agent.action"  # Agent performing an action
    AGENT_THINKING = "agent.thinking"  # Agent reasoning/planning
    AGENT_DECISION = "agent.decision"  # Agent making a decision

    # LLM interaction kinds
    LLM_CALL = "llm.call"  # LLM API call

    # Workflow kinds
    WORKFLOW_STEP = "workflow.step"  # Step in a workflow
    WORKFLOW = AgentOpsSpanKindValues.WORKFLOW.value
    SESSION = AgentOpsSpanKindValues.SESSION.value
    TASK = AgentOpsSpanKindValues.TASK.value
    OPERATION = AgentOpsSpanKindValues.OPERATION.value
    AGENT = AgentOpsSpanKindValues.AGENT.value
    TOOL = AgentOpsSpanKindValues.TOOL.value
    LLM = AgentOpsSpanKindValues.LLM.value
    UNKNOWN = AgentOpsSpanKindValues.UNKNOWN.value
    CHAIN = AgentOpsSpanKindValues.CHAIN.value
    TEXT = AgentOpsSpanKindValues.TEXT.value
    GUARDRAIL = AgentOpsSpanKindValues.GUARDRAIL.value
    HTTP = AgentOpsSpanKindValues.HTTP.value
