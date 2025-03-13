"""Span kinds for AgentOps."""

from enum import Enum


class SpanKind:
    """Defines the kinds of spans in AgentOps."""

    # Agent action kinds
    AGENT_ACTION = "agent.action"  # Agent performing an action
    AGENT_THINKING = "agent.thinking"  # Agent reasoning/planning
    AGENT_DECISION = "agent.decision"  # Agent making a decision

    # LLM interaction kinds
    LLM_CALL = "llm.call"  # LLM API call

    # Workflow kinds
    WORKFLOW_STEP = "workflow.step"  # Step in a workflow
    SESSION = "session"
    TASK = "task"
    OPERATION = "operation"
    AGENT = "agent"
    TOOL = "tool"
    LLM = "llm"
    TEAM = "team"
    UNKNOWN = "unknown"


class AgentOpsSpanKindValues(Enum):
    WORKFLOW = "workflow"
    TASK = "task"
    AGENT = "agent"
    TOOL = "tool"
    LLM = "llm"
    TEAM = "team"
    UNKNOWN = "unknown"
