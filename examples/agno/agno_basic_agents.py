"""
# Basic Agents and Teams with Agno

This example demonstrates the fundamentals of creating AI agents and organizing them into collaborative teams using the Agno framework.

## Overview

In this example, you'll learn how to:
- **Create specialized AI agents** with specific roles and expertise
- **Organize agents into teams** for collaborative problem-solving
- **Use coordination modes** for effective agent communication
- **Monitor agent interactions** with AgentOps integration

## Key Concepts

### Agents
Individual AI entities with specific roles and capabilities. Each agent can be assigned a particular area of expertise, making them specialists in their domain.

### Teams
Collections of agents that work together to solve complex tasks. Teams can coordinate their responses, share information, and delegate tasks based on each agent's expertise.

### Coordination Modes
Different strategies for how agents within a team interact and collaborate. The "coordinate" mode enables intelligent task routing and information sharing.
"""

import os
from dotenv import load_dotenv
import agentops
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat

load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_agentops_api_key_here")

agentops.init(
    auto_start_session=False, trace_name="Agno Basic Agents", tags=["agno-example", "basics", "agents-and-teams"]
)


def demonstrate_basic_agents():
    """
    Demonstrate basic agent creation and team coordination.

    This function shows how to:
    1. Create specialized agents with specific roles
    2. Organize agents into a team
    3. Use the team to solve tasks that require multiple perspectives
    """
    tracer = agentops.start_trace(trace_name="Agno Basic Agents and Teams Demonstration")

    try:
        # Create individual agents with specific roles
        # Each agent has a name and a role that defines its expertise

        # News Agent: Specializes in gathering and analyzing news information
        news_agent = Agent(
            name="News Agent", role="Get the latest news and provide news analysis", model=OpenAIChat(id="gpt-4o-mini")
        )

        # Weather Agent: Specializes in weather forecasting and analysis
        weather_agent = Agent(
            name="Weather Agent",
            role="Get weather forecasts and provide weather analysis",
            model=OpenAIChat(id="gpt-4o-mini"),
        )

        # Create a team with coordination mode
        # The "coordinate" mode allows agents to work together and share information
        team = Team(
            name="News and Weather Team",
            mode="coordinate",  # Agents will coordinate their responses
            members=[news_agent, weather_agent],
        )

        # Run a task that requires team coordination
        # The team will automatically determine which agent(s) should respond
        response = team.run("What is the weather in Tokyo?")

        print("\nTeam Response:")
        print("-" * 60)
        print(f"{response.content}")
        print("-" * 60)

        agentops.end_trace(tracer, end_state="Success")

    except Exception as e:
        print(f"An error occurred: {e}")
        agentops.end_trace(tracer, end_state="Error")

    # Let's check programmatically that spans were recorded in AgentOps
    print("\n" + "=" * 50)
    print("Now let's verify that our LLM calls were tracked properly...")
    try:
        agentops.validate_trace_spans(trace_context=tracer)
        print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
    except agentops.ValidationError as e:
        print(f"\n❌ Error validating spans: {e}")
        raise


if __name__ == "__main__":
    demonstrate_basic_agents()
