"""Defines the kinds of spans in AgentOps."""

class SpanKind:
    """Defines the kinds of spans in AgentOps."""
    
    # Core span kinds
    SESSION = "session"                # Root span for a session
    AGENT = "agent"                    # Agent instance
    TOOL = "tool"                      # Tool execution
    
    # Agent action kinds
    AGENT_ACTION = "agent.action"      # Agent performing an action
    AGENT_THINKING = "agent.thinking"  # Agent reasoning/planning
    AGENT_DECISION = "agent.decision"  # Agent making a decision
    
    # LLM interaction kinds
    LLM_CALL = "llm.call"              # LLM API call
    LLM_STREAM = "llm.stream"          # Streaming LLM response
    
    # Workflow kinds
    WORKFLOW_STEP = "workflow.step"    # Step in a workflow
    WORKFLOW_TASK = "workflow.task"    # Task in a workflow
