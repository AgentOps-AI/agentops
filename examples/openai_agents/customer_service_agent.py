# Airline Customer Service Agent
#
# This is a simple chatbot designed to assist airline customers with common queries. Here the agents are also used as tools to help the bot answer questions more effectively.
#
# Using AgentOps we can track the flow of the conversation and the agents used. This is useful for debugging and understanding how the bot is performing.
# ## Prerequisites
#
# Before running this notebook, you'll need:
#
# 1. **AgentOps Account**: Create a free account at [app.agentops.ai](https://app.agentops.ai)
# 2. **AgentOps API Key**: Obtain your API key from your AgentOps dashboard
# 3. **OpenAI API Key**: Get your API key from [platform.openai.com](https://platform.openai.com)
#
# Make sure to set these as environment variables or create a `.env` file in your project root with:
#
# ```
# AGENTOPS_API_KEY=your_agentops_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here
# ```
# # Install required packages
# %pip install agentops
# %pip install openai-agents
# %pip install pydotenv
# Set the API keys for your AgentOps and OpenAI accounts.
from __future__ import annotations as _annotations

import os
from dotenv import load_dotenv
import random
import uuid
import asyncio

from pydantic import BaseModel
import agentops

from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    handoff,
    trace,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

load_dotenv()

os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

agentops.init(
    trace_name="OpenAI Agents Customer Service",
    tags=["customer-service-agent", "openai-agents", "agentops-example"],
    auto_start_session=False,
)
tracer = agentops.start_trace(trace_name="OpenAI Agents Customer Service Agent")


# Context model for the airline agent
class AirlineAgentContext(BaseModel):
    passenger_name: str | None = None
    confirmation_number: str | None = None
    seat_number: str | None = None
    flight_number: str | None = None


# Tools for the airline agent
@function_tool(name_override="faq_lookup_tool", description_override="Lookup frequently asked questions.")
async def faq_lookup_tool(question: str) -> str:
    if "bag" in question or "baggage" in question:
        return (
            "You are allowed to bring one bag on the plane. "
            "It must be under 50 pounds and 22 inches x 14 inches x 9 inches."
        )
    elif "seats" in question or "plane" in question:
        return (
            "There are 120 seats on the plane. "
            "There are 22 business class seats and 98 economy seats. "
            "Exit rows are rows 4 and 16. "
            "Rows 5-8 are Economy Plus, with extra legroom. "
        )
    elif "wifi" in question:
        return "We have free wifi on the plane, join Airline-Wifi"
    return "I'm sorry, I don't know the answer to that question."


@function_tool
async def update_seat(context: RunContextWrapper[AirlineAgentContext], confirmation_number: str, new_seat: str) -> str:
    """
    Update the seat for a given confirmation number.

    Args:
        confirmation_number: The confirmation number for the flight.
        new_seat: The new seat to update to.
    """
    # Update the context based on the customer's input
    context.context.confirmation_number = confirmation_number
    context.context.seat_number = new_seat
    # Ensure that the flight number has been set by the incoming handoff
    assert context.context.flight_number is not None, "Flight number is required"
    return f"Updated seat to {new_seat} for confirmation number {confirmation_number}"


# HOOKS
async def on_seat_booking_handoff(context: RunContextWrapper[AirlineAgentContext]) -> None:
    flight_number = f"FLT-{random.randint(100, 999)}"
    context.context.flight_number = flight_number


# AGENTS
faq_agent = Agent[AirlineAgentContext](
    name="FAQ Agent",
    handoff_description="A helpful agent that can answer questions about the airline.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an FAQ agent. If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Identify the last question asked by the customer.
    2. Use the faq lookup tool to answer the question. Do not rely on your own knowledge.
    3. If you cannot answer the question, transfer back to the triage agent.""",
    tools=[faq_lookup_tool],
)

seat_booking_agent = Agent[AirlineAgentContext](
    name="Seat Booking Agent",
    handoff_description="A helpful agent that can update a seat on a flight.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a seat booking agent. If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Ask for their confirmation number.
    2. Ask the customer what their desired seat number is.
    3. Use the update seat tool to update the seat on the flight.
    If the customer asks a question that is not related to the routine, transfer back to the triage agent. """,
    tools=[update_seat],
)

triage_agent = Agent[AirlineAgentContext](
    name="Triage Agent",
    handoff_description="A triage agent that can delegate a customer's request to the appropriate agent.",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX} "
        "You are a helpful triaging agent. You can use your tools to delegate questions to other appropriate agents."
    ),
    handoffs=[
        faq_agent,
        handoff(agent=seat_booking_agent, on_handoff=on_seat_booking_handoff),
    ],
)

faq_agent.handoffs.append(triage_agent)
seat_booking_agent.handoffs.append(triage_agent)


async def main():
    current_agent: Agent[AirlineAgentContext] = triage_agent
    input_items: list[TResponseInputItem] = []
    context = AirlineAgentContext()

    # Normally, each input from the user would be an API request to your app, and you can wrap the request in a trace()
    # Here, we'll just use a random UUID for the conversation ID
    conversation_id = uuid.uuid4().hex[:16]

    # Predefined test messages to demonstrate the customer service agent
    test_messages = [
        "Hello, I need help with my flight",
        "I want to change my seat",
        "My confirmation number is ABC123",
        "I'd like seat 12A please",
        "What's the baggage policy?",
        "How many seats are on the plane?",
        "Is there wifi on the flight?",
        "Thank you for your help",
    ]

    print("🤖 Starting Customer Service Agent Demo")
    print("=" * 50)

    for user_input in test_messages:
        print(f"\n👤 User: {user_input}")

        with trace("Customer service", group_id=conversation_id):
            input_items.append({"content": user_input, "role": "user"})
            result = await Runner.run(current_agent, input_items, context=context)

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    print(f"🤖 {agent_name}: {ItemHelpers.text_message_output(new_item)}")
                elif isinstance(new_item, HandoffOutputItem):
                    print(f"🔄 Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}")
                elif isinstance(new_item, ToolCallItem):
                    print(f"🔧 {agent_name}: Calling a tool")
                elif isinstance(new_item, ToolCallOutputItem):
                    print(f"🔧 {agent_name}: Tool call output: {new_item.output}")
                else:
                    print(f"ℹ️  {agent_name}: Skipping item: {new_item.__class__.__name__}")
            input_items = result.to_input_list()
            current_agent = result.last_agent

    print("\n" + "=" * 50)
    print("🎉 Customer Service Agent Demo Complete!")


if __name__ == "__main__":
    asyncio.run(main())

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=tracer)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise


# ## Conclusion
#
# **AgentOps makes observability effortless** - simply import the library and all your interactions are automatically tracked, visualized, and analyzed. This enables you to:
#
# - Monitor tool performance across different use cases
# - Optimize costs by understanding tool usage patterns
# - Debug tool integration issues quickly
# - Scale your AI applications with confidence in tool reliability
#
# Visit [app.agentops.ai](https://app.agentops.ai) to explore your tool usage sessions and gain deeper insights into your AI application's tool interactions.
