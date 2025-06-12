"""
Basic Agents and Teams with Agno

This example demonstrates the fundamentals of creating AI agents and organizing them into teams
using the Agno framework. You'll learn how to:
- Create individual agents with specific roles
- Combine agents into teams for collaborative problem-solving
- Use coordination modes for effective agent communication
"""

import os
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
import asyncio
import agentops
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize AgentOps for monitoring and analytics
agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

# Configuration
MODEL_ID = "gpt-4o-mini"  # Using OpenAI's cost-effective model

def check_environment():
    """
    Verify that all required API keys are properly configured.
    
    Returns:
        bool: True if all required environment variables are set
    """
    required_vars = ["AGENTOPS_API_KEY", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Missing required environment variables: {missing_vars}")
        print("Please set these in your .env file or environment")
        return False

    print("✓ Environment variables checked successfully")
    return True


def demonstrate_basic_agents():
    """
    Demonstrate basic agent creation and team coordination.
    
    This function shows how to:
    1. Create specialized agents with specific roles
    2. Organize agents into a team
    3. Use the team to solve tasks that require multiple perspectives
    """
    print("\n" + "=" * 60)
    print("BASIC AGENTS AND TEAMS DEMONSTRATION")
    print("=" * 60)

    try:
        # Create individual agents with specific roles
        # Each agent has a name and a role that defines its expertise
        
        print("\n1. Creating specialized agents...")
        
        # News Agent: Specializes in gathering and analyzing news information
        news_agent = Agent(
            name="News Agent", 
            role="Get the latest news and provide news analysis", 
            model=OpenAIChat(id=MODEL_ID)
        )
        print("   ✓ News Agent created")

        # Weather Agent: Specializes in weather forecasting and analysis
        weather_agent = Agent(
            name="Weather Agent", 
            role="Get weather forecasts and provide weather analysis", 
            model=OpenAIChat(id=MODEL_ID)
        )
        print("   ✓ Weather Agent created")

        # Create a team with coordination mode
        # The "coordinate" mode allows agents to work together and share information
        print("\n2. Creating a team with coordination capabilities...")
        team = Team(
            name="News and Weather Team", 
            mode="coordinate",  # Agents will coordinate their responses
            members=[news_agent, weather_agent]
        )
        print("   ✓ Team created with 2 agents")

        # Run a task that requires team coordination
        # The team will automatically determine which agent(s) should respond
        print("\n3. Running team task...")
        print("   Query: 'What is the weather in Tokyo?'")
        
        response = team.run("What is the weather in Tokyo?")
        
        print("\n4. Team Response:")
        print("-" * 60)
        print(f"{response.content}")
        print("-" * 60)
        
        # The team intelligently routes the query to the Weather Agent
        # since it's weather-related, demonstrating smart task delegation

    except Exception as e:
        print(f"Error during basic agents demonstration: {e}")
        print("This might be due to API issues or configuration problems")


async def main():
    """
    Main function that orchestrates the demonstration.
    
    This async function handles:
    - Environment validation
    - Running the basic agents demonstration
    - Error handling and user feedback
    """
    print("Welcome to Agno Basic Agents Demo")
    print("This demo shows how to create and coordinate AI agents")
    print()
    
    # Validate environment setup
    if not check_environment():
        print("Cannot proceed without proper API configuration")
        return

    # Run demonstrations
    print("\nStarting demonstrations...")

    # Basic agents and teams demonstration
    try:
        demonstrate_basic_agents()
        print("\n✓ Demo completed successfully!")
        print("\nKey Takeaways:")
        print("- Agents can have specialized roles and expertise")
        print("- Teams enable multiple agents to collaborate on tasks")
        print("- Coordination mode allows intelligent task delegation")
        print("- AgentOps tracks all agent interactions for monitoring")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        print("Please check your API keys and network connection")


if __name__ == "__main__":
    """
    Entry point for the script.
    
    Uses asyncio to run the main function, preparing for future
    async operations and maintaining consistency with other examples.
    """
    asyncio.run(main())
