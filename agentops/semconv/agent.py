"""Attributes specific to agent spans."""

class AgentAttributes:
    """Attributes specific to agent spans."""
    
    # Identity
    AGENT_ID = "agent.id"                  # Unique identifier for the agent
    AGENT_NAME = "agent.name"              # Name of the agent
    AGENT_ROLE = "agent.role"              # Role of the agent
    
    # Capabilities
    AGENT_TOOLS = "agent.tools"            # Tools available to the agent
    AGENT_MODELS = "agent.models"          # Models available to the agent
    
    # State
    AGENT_STATUS = "agent.status"          # Current status of the agent
    
    # Reasoning
    AGENT_REASONING = "agent.reasoning"    # Agent's reasoning process
