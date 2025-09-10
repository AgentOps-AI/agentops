# Microsoft Autogen Group Chat Example
#
# AgentOps automatically configures itself when it's initialized meaning your agent run data will be tracked and logged to your AgentOps dashboard right away.
# First let's install the required packages
# %pip install -U "ag2[autogen-agentchat]"
# %pip install -U "autogen-ext[openai]"
# %pip install -U agentops
# %pip install -U python-dotenv


import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
import agentops
from dotenv import load_dotenv
import nest_asyncio

load_dotenv()
agentops.init(auto_start_session=False, tags=["autogen-group-chat", "agentops-example"])
tracer = agentops.start_trace(trace_name="autogen-group-chat")


# Define mock tools for the agents:
# - search_web_tool: Simulates web search results for specific basketball queries (used by the WebSearchAgent).
# - percentage_change_tool: Calculates the percentage change between two numbers (used by the DataAnalystAgent).
def search_web_tool(query: str) -> str:
    if "2006-2007" in query:
        return """Here are the total points scored by Miami Heat players in the 2006-2007 season:
        Udonis Haslem: 844 points
        Dwayne Wade: 1397 points
        James Posey: 550 points
        ...
        """
    elif "2007-2008" in query:
        return "The number of total rebounds for Dwayne Wade in the Miami Heat season 2007-2008 is 214."
    elif "2008-2009" in query:
        return "The number of total rebounds for Dwayne Wade in the Miami Heat season 2008-2009 is 398."
    return "No data found."


def percentage_change_tool(start: float, end: float) -> float:
    return ((end - start) / start) * 100


model_client = OpenAIChatCompletionClient(model="gpt-4o")
# Define the planning agent responsible for breaking down tasks and delegating them to other agents.
planning_agent = AssistantAgent(
    "PlanningAgent",
    description="An agent for planning tasks, this agent should be the first to engage when given a new task.",
    model_client=model_client,
    system_message="""
    You are a planning agent.
    Your job is to break down complex tasks into smaller, manageable subtasks.
    Your team members are:
        WebSearchAgent: Searches for information
        DataAnalystAgent: Performs calculations

    You only plan and delegate tasks - you do not execute them yourself.

    When assigning tasks, use this format:
    1. <agent> : <task>

    After all tasks are complete, summarize the findings and end with "TERMINATE".
    """,
)

# The web search agent that is responsible for retrieving information using the search tool.
web_search_agent = AssistantAgent(
    "WebSearchAgent",
    description="An agent for searching information on the web.",
    tools=[search_web_tool],
    model_client=model_client,
    system_message="""
    You are a web search agent.
    Your only tool is search_tool - use it to find information.
    You make only one search call at a time.
    Once you have the results, you never do calculations based on them.
    """,
)

# The data analyst agent that is responsible for performing calculations using the provided tool.
data_analyst_agent = AssistantAgent(
    "DataAnalystAgent",
    description="An agent for performing calculations.",
    model_client=model_client,
    tools=[percentage_change_tool],
    system_message="""
    You are a data analyst.
    Given the tasks you have been assigned, you should analyze the data and provide results using the tools provided.
    If you have not seen the data, ask for it.
    """,
)


# These rules decide when the group chat should stop:
# - If someone says 'TERMINATE' in the chat, or
# - If the chat goes on for too many messages (25 turns)
text_mention_termination = TextMentionTermination("TERMINATE")
max_messages_termination = MaxMessageTermination(max_messages=25)
termination = text_mention_termination | max_messages_termination

# This is a message that helps the system pick which agent (helper) should talk next.
# It looks at what has happened so far and chooses the best agent for the next step.
selector_prompt = """Select an agent to perform task.
{roles}
Current conversation context:
{history}
Read the above conversation, then select an agent from {participants} to perform the next task.
Make sure the planner agent has assigned tasks before other agents start working.
Only select one agent.
"""

# Here we put all our agents (helpers) together into a team.
# The team will work together to solve the problem, following the rules above.
team = SelectorGroupChat(
    [planning_agent, web_search_agent, data_analyst_agent],
    model_client=model_client,
    termination_condition=termination,
    selector_prompt=selector_prompt,
    allow_repeated_speaker=True,  # Allow an agent to speak multiple turns in a row.
)
task = "Who was the Miami Heat player with the highest points in the 2006-2007 season, and what was the percentage change in his total rebounds between the 2007-2008 and 2008-2009 seasons?"

nest_asyncio.apply()
asyncio.run(Console(team.run_stream(task=task)))

# You can view data on this run at [app.agentops.ai](app.agentops.ai).

# The dashboard will display LLM events for each message sent by each agent, including those made by the human user.
