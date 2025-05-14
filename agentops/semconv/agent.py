"""Attributes specific to agent spans."""


class AgentAttributes:
    """Attributes specific to agent spans."""

    # Identity
    AGENT_ID = "agent.id"  # Unique identifier for the agent
    AGENT_NAME = "agent.name"  # Name of the agent
    AGENT_ROLE = "agent.role"  # Role of the agent
    AGENT = "agent"  # Root prefix for agent attributes

    # Capabilities
    AGENT_TOOLS = "agent.tools"  # Tools available to the agent
    AGENT_MODELS = "agent.models"  # Models available to the agent

    TOOLS = "tools"
    HANDOFFS = "handoffs"

    # NOTE: This attribute deviates from the OpenTelemetry GenAI semantic conventions.
    # According to OpenTelemetry GenAI conventions, this should be named "gen_ai.agent.source"
    # or follow a similar pattern under the "gen_ai" namespace.
    FROM_AGENT = "from_agent"

    # NOTE: This attribute deviates from the OpenTelemetry GenAI semantic conventions.
    # According to OpenTelemetry GenAI conventions, this should be named "gen_ai.agent.destination"
    # or follow a similar pattern under the "gen_ai" namespace.
    TO_AGENT = "to_agent"

    AGENT_REASONING = "agent.reasoning"
