# Microsoft Autogen Swarm Team Example
#
# This example shows how you can have two AI agents work together to help a user refund a flight.
# Each agent has a special job, and they can "handoff" the conversation to each other or to the user as needed.
# All actions are tracked by AgentOps so you can see what happened in your dashboard.

# First let's install the required packages
# %pip install -U ag2[autogen-agentchat]
# %pip install -U "autogen-ext[openai]"
# %pip install -U agentops
# %pip install -U python-dotenv
# %pip install -U nest_asyncio

# Then import them
from typing import Any, Dict, List
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import HandoffTermination, TextMentionTermination
from autogen_agentchat.messages import HandoffMessage
from autogen_agentchat.teams import Swarm
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
import os
import agentops
from dotenv import load_dotenv
import nest_asyncio

# Load environment variables (like API keys)
load_dotenv()
# Set up AgentOps to track everything that happens in this session
agentops.init(auto_start_session=False, tags=["autogen-swarm-team", "agentops-example"])
tracer = agentops.start_trace(trace_name="autogen-swarm-team")

# This is a pretend tool that "refunds" a flight when given a flight ID.
def refund_flight(flight_id: str) -> str:
    """Refund a flight"""
    return f"Flight {flight_id} refunded"

# Set up the AI model client (the brain for the agents)
model_client = OpenAIChatCompletionClient(
    model="gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY", "your_openai_api_key_here"),
)

# The travel agent helps with travel tasks and can hand off to the flights_refunder agent.
travel_agent = AssistantAgent(
    "travel_agent",
    model_client=model_client,
    handoffs=["flights_refunder", ""],
    system_message="""You are a travel agent.
    The flights_refunder is in charge of refunding flights.
    If you need information from the user, you must first send your message, then you can handoff to the user.
    Use TERMINATE when the travel planning is complete.""",
)

# The flights_refunder agent specializes in refunding flights and can use the refund_flight tool.
flights_refunder = AssistantAgent(
    "flights_refunder",
    model_client=model_client,
    handoffs=["travel_agent", "user"],
    tools=[refund_flight],
    system_message="""You are an agent specialized in refunding flights.
    You only need flight reference numbers to refund a flight.
    You have the ability to refund a flight using the refund_flight tool.
    If you need information from the user, you must first send your message, then you can handoff to the user.
    When the transaction is complete, handoff to the travel agent to finalize.""",
)

# These rules decide when the conversation should stop:
# - If the user is handed the conversation (handoff to user), or
# - If someone says 'TERMINATE' in the chat
termination = HandoffTermination(target="user") | TextMentionTermination("TERMINATE")
# Put both agents together into a "Swarm" team so they can work together.
team = Swarm([travel_agent, flights_refunder], termination_condition=termination)
# This is the task the user wants help with.
task = "I need to refund my flight."

# This function runs the team and handles the back-and-forth with the user.
async def run_team_stream() -> None:
    task_result = await Console(team.run_stream(task=task))
    last_message = task_result.messages[-1]

    # These are the user's replies, sent automatically to keep the example running.
    scripted_responses = [
        "My flight reference is ABC123.",
        "Yes, thank you. TERMINATE",
    ]
    response_index = 0

    # Keep going as long as the agents hand the conversation to the user.
    while isinstance(last_message, HandoffMessage) and last_message.target == "user":
        if response_index >= len(scripted_responses):
            break  # Stop if we run out of replies

        user_message = scripted_responses[response_index]
        response_index += 1

        task_result = await Console(
            team.run_stream(
                task=HandoffMessage(
                    source="user", target=last_message.source, content=user_message
                )
            )
        )
        last_message = task_result.messages[-1]

# Start the team and let the agents and user work together to solve the problem.
nest_asyncio.apply()
asyncio.run(run_team_stream())

