"""
Collaborative Research Team with Agno

This example demonstrates how to create a sophisticated research team with multiple specialized agents,
each equipped with different tools and expertise. The team collaborates to research topics from
multiple perspectives, providing comprehensive insights.

Key features demonstrated:
- Creating specialized agents with specific research tools
- Building collaborative teams that discuss and reach consensus
- Using various research tools (Google Search, HackerNews, Arxiv, DuckDuckGo)
- Enabling real-time streaming of agent discussions
- Tracking agent interactions with AgentOps
"""

import os
from textwrap import dedent
from agno.agent import Agent
from agno.team import Team
from agno.tools.googlesearch import GoogleSearchTools
from agno.tools.hackernews import HackerNewsTools
from agno.tools.arxiv import ArxivTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat
import asyncio
import agentops
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize AgentOps for monitoring and analytics
agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

# Configuration
MODEL_ID = "gpt-4o-mini"  # Default model for agents

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

def demonstrate_research_team():
    """
    Demonstrate a collaborative research team with multiple specialized agents.
    
    This function creates a team of researchers, each with:
    - Specific expertise and research focus
    - Specialized tools for their domain
    - Custom instructions for their research approach
    
    The team collaborates to provide comprehensive research insights.
    """
    print("\n" + "=" * 60)
    print("COLLABORATIVE RESEARCH TEAM DEMONSTRATION")
    print("=" * 60)

    try:
        print("\n1. Creating specialized research agents...")
        
        # Reddit Researcher: Focuses on community discussions and user experiences
        reddit_researcher = Agent(
            name="Reddit Researcher",
            role="Research a topic on Reddit",
            model=OpenAIChat(id="gpt-4o"),  # Using more capable model for research
            tools=[GoogleSearchTools()],  # Google Search to find Reddit discussions
            add_name_to_instructions=True,  # Adds agent name to its instructions
            instructions=dedent(
                """
                You are a Reddit researcher specializing in community insights.
                You will be given a topic to research on Reddit.
                Your tasks:
                - Find the most relevant and popular Reddit posts
                - Identify common opinions and experiences from users
                - Highlight both positive and negative perspectives
                - Focus on practical advice and real-world experiences
            """
            ),
        )
        print("   ✓ Reddit Researcher created")

        # HackerNews Researcher: Focuses on technical discussions and industry trends
        hackernews_researcher = Agent(
            name="HackerNews Researcher",
            model=OpenAIChat("gpt-4o"),
            role="Research a topic on HackerNews.",
            tools=[HackerNewsTools()],  # Direct access to HackerNews API
            add_name_to_instructions=True,
            instructions=dedent(
                """
                You are a HackerNews researcher specializing in technical insights.
                You will be given a topic to research on HackerNews.
                Your tasks:
                - Find the most relevant technical discussions
                - Identify industry trends and expert opinions
                - Focus on technical depth and innovation
                - Highlight startup and technology perspectives
            """
            ),
        )
        print("   ✓ HackerNews Researcher created")

        # Academic Paper Researcher: Focuses on scholarly research and evidence
        academic_paper_researcher = Agent(
            name="Academic Paper Researcher",
            model=OpenAIChat("gpt-4o"),
            role="Research academic papers and scholarly content",
            tools=[GoogleSearchTools(), ArxivTools()],  # Multiple tools for comprehensive research
            add_name_to_instructions=True,
            instructions=dedent(
                """
                You are an academic paper researcher specializing in scholarly content.
                You will be given a topic to research in academic literature.
                Your tasks:
                - Find relevant scholarly articles, papers, and academic discussions
                - Focus on peer-reviewed content and citations from reputable sources
                - Provide brief summaries of key findings and methodologies
                - Highlight evidence-based conclusions and research gaps
            """
            ),
        )
        print("   ✓ Academic Paper Researcher created")

        # Twitter Researcher: Focuses on real-time trends and public sentiment
        twitter_researcher = Agent(
            name="Twitter Researcher",
            model=OpenAIChat("gpt-4o"),
            role="Research trending discussions and real-time updates",
            tools=[DuckDuckGoTools()],  # DuckDuckGo for privacy-focused searching
            add_name_to_instructions=True,
            instructions=dedent(
                """
                You are a Twitter/X researcher specializing in real-time insights.
                You will be given a topic to research on Twitter/X.
                Your tasks:
                - Find trending discussions and influential voices
                - Track real-time updates and breaking news
                - Focus on verified accounts and credible sources
                - Identify relevant hashtags and ongoing conversations
                - Capture public sentiment and viral content
            """
            ),
        )
        print("   ✓ Twitter Researcher created")

        # Create collaborative team with advanced features
        print("\n2. Creating collaborative research team...")
        agent_team = Team(
            name="Discussion Team",
            mode="collaborate",  # Agents work together and discuss findings
            model=OpenAIChat("gpt-4o"),  # Model for team coordination
            members=[
                reddit_researcher,
                hackernews_researcher,
                academic_paper_researcher,
                twitter_researcher,
            ],
            instructions=[
                "You are a discussion master coordinating a research team.",
                "Facilitate productive discussion between all researchers.",
                "Ensure each researcher contributes their unique perspective.",
                "Guide the team towards a comprehensive understanding of the topic.",
                "You have to stop the discussion when you think the team has reached a consensus.",
            ],
            success_criteria="The team has reached a consensus with insights from all perspectives.",
            enable_agentic_context=True,  # Agents maintain context throughout discussion
            add_context=True,  # Include context in agent responses
            show_tool_calls=True,  # Display when agents use their tools
            markdown=True,  # Format output in markdown
            debug_mode=True,  # Show detailed execution information
            show_members_responses=True,  # Display individual agent responses
        )
        print("   ✓ Research team assembled with 4 specialized agents")

        # Execute collaborative research
        print("\n3. Starting collaborative research discussion...")
        print("   Topic: 'What is the best way to learn to code?'")
        print("\n" + "-" * 60)
        
        # Stream the team discussion in real-time
        agent_team.print_response(
            message="Start the discussion on the topic: 'What is the best way to learn to code?'",
            stream=True,  # Stream responses as they're generated
            stream_intermediate_steps=True,  # Show intermediate thinking steps
        )

    except Exception as e:
        print(f"\nError during research team demonstration: {e}")
        print("This might be due to API rate limits or configuration issues")


async def main():
    """
    Main function that orchestrates the research team demonstration.
    
    This async function handles:
    - Environment validation
    - Running the collaborative research team demo
    - Error handling and user feedback
    """
    print("Welcome to Agno Collaborative Research Team Demo")
    print("This demo shows how multiple specialized agents can work together")
    print("to provide comprehensive research insights from different perspectives.")
    print()
    
    # Validate environment setup
    if not check_environment():
        print("Cannot proceed without proper API configuration")
        return

    # Run demonstration
    print("\nStarting research team demonstration...")

    try:
        demonstrate_research_team()
        print("\n\n✓ Research team demo completed successfully!")
        print("\nKey Takeaways:")
        print("- Specialized agents bring unique perspectives and tools")
        print("- Collaborative mode enables rich discussions between agents")
        print("- Each agent uses appropriate tools for their research domain")
        print("- Teams can reach consensus through structured discussion")
        print("- AgentOps tracks all interactions for analysis")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        print("Please check your API keys and network connection")


if __name__ == "__main__":
    """
    Entry point for the script.
    
    Uses asyncio to run the main function, maintaining consistency
    with other examples and preparing for async operations.
    """
    asyncio.run(main())
