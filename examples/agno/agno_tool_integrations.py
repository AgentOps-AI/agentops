"""
# Tool Integration Example with Agno

This example demonstrates how to integrate and use various tools with Agno agents,
showing how AgentOps automatically tracks tool usage and agent interactions.

## Overview
This example demonstrates:

1. **Using built-in Agno tools** like GoogleSearch, DuckDuckGo, and Arxiv
2. **Creating agents with tools** and seeing how they use them
3. **Tool execution tracking** with AgentOps
4. **Combining multiple tools** for comprehensive research

This example uses actual Agno components to show real tool integration patterns.
"""

import os
from dotenv import load_dotenv
import agentops
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.googlesearch import GoogleSearchTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.arxiv import ArxivTools

# Load environment variables
load_dotenv()

# Set environment variables if not already set
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_agentops_api_key_here")

# Initialize AgentOps
agentops.init(
    auto_start_session=False, trace_name="Agno Tool Integrations", tags=["agno-tools", "tool-integration", "demo"]
)


def demonstrate_tool_integration():
    """Demonstrate tool integration with Agno agents."""
    print("🚀 Agno Tool Integration Demonstration")
    print("=" * 60)

    # Start AgentOps trace
    tracer = agentops.start_trace(trace_name="Agno Tool Integration Demo")

    try:
        # Example 1: Single Tool Agent
        print("\n📌 Example 1: Agent with Google Search Tool")
        print("-" * 40)

        search_agent = Agent(
            name="Search Agent",
            role="Research information using Google Search",
            model=OpenAIChat(id="gpt-4o-mini"),
            tools=[GoogleSearchTools()],
            instructions="You are a research assistant. Use Google Search to find accurate, up-to-date information.",
        )

        response = search_agent.run("What are the latest developments in AI agents?")
        print(f"Search Agent Response:\n{response.content}")

        # Example 2: Multi-Tool Agent
        print("\n\n📌 Example 2: Agent with Multiple Tools")
        print("-" * 40)

        research_agent = Agent(
            name="Research Agent",
            role="Comprehensive research using multiple tools",
            model=OpenAIChat(id="gpt-4o-mini"),
            tools=[GoogleSearchTools(), ArxivTools(), DuckDuckGoTools()],
            instructions="""You are a comprehensive research assistant. 
            Use Google Search for general information, Arxiv for academic papers, 
            and DuckDuckGo as an alternative search engine. 
            Provide well-researched, balanced information from multiple sources.""",
        )

        response = research_agent.run(
            "Find information about recent advances in tool-use for AI agents. "
            "Include both academic research and practical implementations."
        )
        print(f"Research Agent Response:\n{response.content}")

        # Example 3: Specialized Tool Usage
        print("\n\n📌 Example 3: Academic Research with Arxiv")
        print("-" * 40)

        academic_agent = Agent(
            name="Academic Agent",
            role="Find and summarize academic papers",
            model=OpenAIChat(id="gpt-4o-mini"),
            tools=[ArxivTools()],
            instructions="You are an academic research assistant. Use Arxiv to find relevant papers and provide concise summaries.",
        )

        response = academic_agent.run("Find recent papers about tool augmented language models")
        print(f"Academic Agent Response:\n{response.content}")

        # Example 4: Comparing Search Tools
        print("\n\n📌 Example 4: Comparing Different Search Tools")
        print("-" * 40)

        comparison_agent = Agent(
            name="Comparison Agent",
            role="Compare results from different search engines",
            model=OpenAIChat(id="gpt-4o-mini"),
            tools=[GoogleSearchTools(), DuckDuckGoTools()],
            instructions="""Compare search results from Google and DuckDuckGo. 
            Note any differences in results, ranking, or information quality.
            Be objective in your comparison.""",
        )

        response = comparison_agent.run(
            "Search for 'AgentOps observability platform' on both search engines and compare the results"
        )
        print(f"Comparison Agent Response:\n{response.content}")

        print("\n\n✨ Demonstration Complete!")
        print("\nKey Takeaways:")
        print("- Agno agents can use multiple tools seamlessly")
        print("- Tools are automatically invoked based on the agent's task")
        print("- AgentOps tracks all tool executions automatically")
        print("- Different tools serve different purposes (web search, academic search, etc.)")
        print("- Agents can compare and synthesize information from multiple tools")

        # End the AgentOps trace successfully
        print("\n📊 View your tool execution traces in AgentOps:")
        print("   Visit https://app.agentops.ai/ to see detailed analytics")
        agentops.end_trace(tracer, end_state="Success")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        agentops.end_trace(tracer, end_state="Error")
        raise

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
    demonstrate_tool_integration()
