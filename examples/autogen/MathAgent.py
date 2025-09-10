# Microsoft Autogen Tool Example
#
# AgentOps automatically configures itself when it's initialized meaning your agent run data will be tracked and logged to your AgentOps account right away.
# First let's install the required packages
# %pip install -U "autogen-agentchat"
# %pip install -U "autogen-ext[openai]"
# %pip install -U agentops
# %pip install -U python-dotenv
# %pip install -U nest_asyncio

from typing import Annotated, Literal
import asyncio
import nest_asyncio
import os
from dotenv import load_dotenv
import agentops
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken

# Next, we'll set our API keys. There are several ways to do this, the code below is just the most foolproof way for the purposes of this notebook. It accounts for both users who use environment variables and those who just want to set the API Key here in this notebook.
#
# [Get an AgentOps API key](https://agentops.ai/settings/projects)
#
# 1. Create an environment variable in a .env file or other method. By default, the AgentOps `init()` function will look for an environment variable named `AGENTOPS_API_KEY`. Or...
#
# 2. Replace `<your_agentops_key>` below and pass in the optional `api_key` parameter to the AgentOps `init(api_key=...)` function. Remember not to commit your API key to a public repo!
load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

agentops.init(auto_start_session=False, trace_name="Autogen Math Agent Example")
tracer = agentops.start_trace(
    trace_name="Microsoft Autogen Tool Example", tags=["autogen-tool", "microsoft-autogen", "agentops-example"]
)

# Autogen will now start automatically tracking
#
# * LLM prompts and completions
# * Token usage and costs
# * Agent names and actions
# * Correspondence between agents
# * Tool usage
# * Errors
# # Tool Example
# # Define model and API key
model_name = "gpt-4-turbo"
api_key = os.getenv("OPENAI_API_KEY")
# Ensure API key is available
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")
# Create the model client
model_client = OpenAIChatCompletionClient(model=model_name, api_key=api_key, seed=42, temperature=0)
Operator = Literal["+", "-", "*", "/"]


def calculator(a: int, b: int, operator: Annotated[Operator, "operator"]) -> int:
    if operator == "+":
        return a + b
    elif operator == "-":
        return a - b
    elif operator == "*":
        return a * b
    elif operator == "/":
        return int(a / b)
    else:
        raise ValueError("Invalid operator")


async def main():
    # Create an assistant agent that can help with math problems and use the calculator tool.
    assistant = AssistantAgent(
        name="Assistant",
        system_message="You are a helpful AI assistant. You can help with simple calculations. Return 'TERMINATE' when the task is done.",
        model_client=model_client,
        tools=[calculator],
        reflect_on_tool_use=True,
        max_tool_iterations=5,
    )

    # This is the math question we want the assistant to solve.
    initial_task_message = "What is (1423 - 123) / 3 + (32 + 23) * 5?"

    try:
        # Start tracking the assistant's work for the first way of running the task(on_messages method).
        tracer = agentops.start_trace(
            trace_name="autogen-math-agent-on-messages", tags=["autogen-math", "agentops-example"]
        )
        # Ask the assistant to solve the problem .
        await assistant.on_messages([TextMessage(content=initial_task_message, source="user")], CancellationToken())
        agentops.end_trace(tracer, end_state="Success")

        # Start tracking for the second way of running the task(using the run method).
        tracer = agentops.start_trace(trace_name="autogen-math-agent-run", tags=["autogen-math", "agentops-example"])
        # Ask the assistant to solve the problem .
        await assistant.run(
            task=[TextMessage(content=initial_task_message, source="user")], cancellation_token=CancellationToken()
        )

        agentops.end_trace(tracer, end_state="Success")
        # Start tracking for the third way: streaming the assistant's responses as they come in(run_stream method).
        tracer = agentops.start_trace(
            trace_name="autogen-math-agent-run-stream", tags=["autogen-math", "agentops-example"]
        )
        async for message in assistant.run_stream(
            task=[TextMessage(content=initial_task_message, source="user")], cancellation_token=CancellationToken()
        ):
            pass
        agentops.end_trace(tracer, end_state="Success")

        # Start tracking for the fourth way: streaming with on_messages_stream(on_messages_stream method).
        tracer = agentops.start_trace(
            trace_name="autogen-math-agent-on-messages-stream", tags=["autogen-math", "agentops-example"]
        )
        async for message in assistant.on_messages_stream(
            messages=[TextMessage(content=initial_task_message, source="user")], cancellation_token=CancellationToken()
        ):
            pass
        agentops.end_trace(tracer, end_state="Success")

    except Exception as e:
        print(f"An error occurred: {e}")
        agentops.end_trace(tracer, end_state="Error")
    finally:
        # Always close the model client when done.
        await model_client.close()


nest_asyncio.apply()
asyncio.run(main())

# You can see your run in action at [app.agentops.ai](app.agentops.ai). In this example, the AgentOps dashboard will show:
#
# * Agents talking to each other
# * Each use of the `calculator` tool
# * Each call to OpenAI for LLM use
