// Define types for the examples
export type ExampleType = 'function-tool' | 'web-search' | 'multi-agent';

// Helper function to get the API key from the project or use a default
const getApiKey = (projectApiKey?: string) => projectApiKey || 'your_api_key_here';

// Colab button HTML for OpenAI Agents SDK examples
export const getColabButtonHtml = (exampleType: ExampleType): string => {
    const colabUrls = {
        'function-tool':
            'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/openai_agents/agent_patterns.ipynb',
        'web-search':
            'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/openai_agents/agents_tools.ipynb',
        'multi-agent':
            'https://colab.research.google.com/github/AgentOps-AI/agentops/blob/main/examples/openai_agents/customer_service_agent.ipynb'
    };

    return `<a target="_blank" href="${colabUrls[exampleType]}">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>`;
};

// Define the OpenAI Agents SDK examples with proper typing
export const agentsSdkExamples = (projectApiKey?: string): Record<ExampleType, string> => ({
    'function-tool': `import agentops
import asyncio
import os
from dotenv import load_dotenv
from agents import Agent, Runner, function_tool
load_dotenv()

# Set OpenAI API key if not already in environment. 
# You can get your API key from https://platform.openai.com/api-keys
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "<your_openai_api_key>"

agentops.init(api_key="${getApiKey(projectApiKey)}")

@function_tool
def get_weather(city: str) -> str:
    return f"The weather in {city} is sunny."


agent = Agent(
    name="Weather checker",
    instructions="You are a helpful agent that can check the weather in a given city.",
    tools=[get_weather],
)


async def main():
    result = await Runner.run(agent, 
                              input="What's the weather in San Francisco?")
    print(result.final_output)
    # The weather in San Francisco is sunny.


if __name__ == "__main__":
    asyncio.run(main())`,
    'web-search': `import agentops
import asyncio
import os
from dotenv import load_dotenv
from agents import Agent, Runner, WebSearchTool, trace

load_dotenv()

# Set OpenAI API key if not already in environment. 
# You can get your API key from https://platform.openai.com/api-keys
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "<your_openai_api_key>"

agentops.init(api_key="${getApiKey(projectApiKey)}")

async def main():
    agent = Agent(
        name="Web searcher",
        instructions="You are a helpful agent.",
        tools=[WebSearchTool(user_location={"type": "approximate", "city": "New York"})],
    )

    with trace("Web search example"):
        result = await Runner.run(
            agent,
            "search the web for 'local sports news' and give me 1 interesting update in a sentence.",
        )
        print(result.final_output)
        # The New York Giants are reportedly pursuing quarterback Aaron Rodgers after his ...


if __name__ == "__main__":
    asyncio.run(main())`,
    'multi-agent': `import agentops
import asyncio
import random
import uuid
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from __future__ import annotations as _annotations
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

agentops.init(api_key="${getApiKey(projectApiKey)}")

load_dotenv()

# Set OpenAI API key if not already in environment.
# You can get your API key from https://platform.openai.com/api-keys
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "<your_openai_api_key>"


### CONTEXT


class AirlineAgentContext(BaseModel):
    passenger_name: str | None = None
    confirmation_number: str | None = None
    seat_number: str | None = None
    flight_number: str | None = None


### TOOLS


@function_tool(
    name_override="faq_lookup_tool", description_override="Lookup frequently asked questions."
)
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
async def update_seat(
    context: RunContextWrapper[AirlineAgentContext], confirmation_number: str, new_seat: str
) -> str:
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


### HOOKS


async def on_seat_booking_handoff(context: RunContextWrapper[AirlineAgentContext]) -> None:
    flight_number = f"FLT-{random.randint(100, 999)}"
    context.context.flight_number = flight_number


### AGENTS

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


### RUN


async def main():
    current_agent: Agent[AirlineAgentContext] = triage_agent
    input_items: list[TResponseInputItem] = []
    context = AirlineAgentContext()

    # Normally, each input from the user would be an API request to your app, and you can wrap the request in a trace()
    # Here, we'll just use a random UUID for the conversation ID
    conversation_id = uuid.uuid4().hex[:16]

    while True:
        user_input = input("Enter your message: ")
        with trace("Customer service", group_id=conversation_id):
            input_items.append({"content": user_input, "role": "user"})
            result = await Runner.run(current_agent, input_items, context=context)

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)}")
                elif isinstance(new_item, HandoffOutputItem):
                    print(
                        f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
                    )
                elif isinstance(new_item, ToolCallItem):
                    print(f"{agent_name}: Calling a tool")
                elif isinstance(new_item, ToolCallOutputItem):
                    print(f"{agent_name}: Tool call output: {new_item.output}")
                else:
                    print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
            input_items = result.to_input_list()
            current_agent = result.last_agent


if __name__ == "__main__":
    asyncio.run(main())`,
});
