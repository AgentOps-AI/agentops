"""Attributes specific to agent spans."""


class AgentAttributes:
    """Attributes specific to agent spans."""

    # Identity
    AGENT_ID = "agent.id"  # Unique identifier for the agent
    AGENT_NAME = "agent.name"  # Name of the agent
    AGENT_ROLE = "agent.role"  # Role of the agent

    # Capabilities
    AGENT_TOOLS = "agent.tools"  # Tools available to the agent
    AGENT_MODELS = "agent.models"  # Models available to the agent

    TOOLS = "tools"
    HANDOFFS = "handoffs"
    FROM_AGENT = "from_agent"
    TO_AGENT = "to_agent"

    AGENT_REASONING = "agent.reasoning"
