"""
Collaborative Research Team with Agno

This example demonstrates how to create a sophisticated research team with multiple specialized agents,
each equipped with different tools and expertise. The team collaborates to research topics from
multiple perspectives, providing comprehensive insights.

Overview:
---------
This example creates a research team consisting of four specialized agents:

1. Reddit Researcher
   - Focus: Community discussions and user experiences
   - Tools: Google Search (to find Reddit discussions)
   - Expertise: Analyzing user opinions, practical advice, and real-world experiences
   - Role: Provides insights from community perspectives

2. HackerNews Researcher
   - Focus: Technical discussions and industry trends
   - Tools: HackerNews API
   - Expertise: Technical analysis and industry insights
   - Role: Provides technical and startup ecosystem perspectives

3. Academic Paper Researcher
   - Focus: Scholarly research and evidence-based findings
   - Tools: Google Search + Arxiv API
   - Expertise: Academic literature and research methodology
   - Role: Provides evidence-based academic insights

4. Twitter Researcher
   - Focus: Real-time trends and public sentiment
   - Tools: DuckDuckGo Search
   - Expertise: Current events and public opinion
   - Role: Provides real-time social media insights

Team Collaboration:
------------------
- Mode: Collaborative discussion
- Coordination: Team uses GPT-4 for discussion management
- Process:
  1. Each agent researches independently using their tools
  2. Agents share findings and discuss implications
  3. Team works towards consensus through structured discussion
  4. Discussion continues until comprehensive understanding is reached

Features Demonstrated:
---------------------
- Creating specialized agents with specific research tools
- Building collaborative teams that discuss and reach consensus
- Using various research tools (Google Search, HackerNews, Arxiv, DuckDuckGo)
- Enabling real-time streaming of agent discussions
- Tracking agent interactions with AgentOps
"""

from textwrap import dedent
from agno.agent import Agent
from agno.team import Team
from agno.tools.googlesearch import GoogleSearchTools
from agno.tools.hackernews import HackerNewsTools
from agno.tools.arxiv import ArxivTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat
import agentops
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize AgentOps for monitoring and analytics
agentops.init(auto_start_session=False, trace_name="Agno Research Team", tags=["agno-example", "research-team"])


def demonstrate_research_team():
    """
    Demonstrate a collaborative research team with multiple specialized agents.

    This function creates a team of researchers, each with:
    - Specific expertise and research focus
    - Specialized tools for their domain
    - Custom instructions for their research approach

    The team collaborates to provide comprehensive research insights.
    """
    tracer = agentops.start_trace(trace_name="Agno Research Team Demonstration")

    try:
        # Reddit Researcher: Focuses on community discussions and user experiences
        reddit_researcher = Agent(
            name="Reddit Researcher",
            role="Research a topic on Reddit",
            model=OpenAIChat(id="gpt-4o"),
            tools=[GoogleSearchTools()],
            add_name_to_instructions=True,
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

        # HackerNews Researcher: Focuses on technical discussions and industry trends
        hackernews_researcher = Agent(
            name="HackerNews Researcher",
            model=OpenAIChat("gpt-4o"),
            role="Research a topic on HackerNews.",
            tools=[HackerNewsTools()],
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

        # Academic Paper Researcher: Focuses on scholarly research and evidence
        academic_paper_researcher = Agent(
            name="Academic Paper Researcher",
            model=OpenAIChat("gpt-4o"),
            role="Research academic papers and scholarly content",
            tools=[GoogleSearchTools(), ArxivTools()],
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

        # Twitter Researcher: Focuses on real-time trends and public sentiment
        twitter_researcher = Agent(
            name="Twitter Researcher",
            model=OpenAIChat("gpt-4o"),
            role="Research trending discussions and real-time updates",
            tools=[DuckDuckGoTools()],
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

        # Create collaborative team with advanced features
        agent_team = Team(
            name="Discussion Team",
            mode="collaborate",
            model=OpenAIChat("gpt-4o"),
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
            enable_agentic_context=True,
            add_context=True,
            show_tool_calls=True,
            markdown=True,
            debug_mode=True,
            show_members_responses=True,
        )

        # Stream the team discussion in real-time
        agent_team.print_response(
            message="Start the discussion on the topic: 'What is the best way to learn to code?'",
            stream=True,
            stream_intermediate_steps=True,
        )

        agentops.end_trace(tracer, end_state="Success")

    except Exception:
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


demonstrate_research_team()
