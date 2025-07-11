# Microsoft Autogen Chat Example
#
# AgentOps automatically configures itself when it's initialized meaning your agent run data will be tracked and logged to your AgentOps dashboard right away.
# First let's install the required packages
# %pip install -U autogen-agentchat
# %pip install -U "autogen-ext[openai]"
# %pip install -U agentops
# %pip install -U python-dotenv
# Then import them
import os
from dotenv import load_dotenv
import asyncio

import agentops

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.ui import Console

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

# When initializing AgentOps, you can pass in optional tags to help filter sessions
agentops.init(auto_start_session=False, trace_name="Autogen Agent Chat Example")
tracer = agentops.start_trace(
    trace_name="Microsoft Agent Chat Example", tags=["autogen-chat", "microsoft-autogen", "agentops-example"]
)

# AutoGen will now start automatically tracking
#
# * LLM prompts and completions
# * Token usage and costs
# * Agent names and actions
# * Correspondence between agents
# * Tool usage
# * Errors
# # Simple Chat Example
# Define model and API key
model_name = "gpt-4o-mini"  # Or "gpt-4o" / "gpt-4o-mini" as per migration guide examples
api_key = os.getenv("OPENAI_API_KEY")

# Create the model client
model_client = OpenAIChatCompletionClient(model=model_name, api_key=api_key)

# Create the agent that uses the LLM.
assistant = AssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant.",  # Added system message for clarity
    model_client=model_client,
)

user_proxy_initiator = UserProxyAgent("user_initiator")


async def main():
    termination = MaxMessageTermination(max_messages=2)

    group_chat = RoundRobinGroupChat(
        [user_proxy_initiator, assistant],  # Corrected: agents as positional argument
        termination_condition=termination,
    )

    chat_task = "How can I help you today?"
    print(f"User Initiator: {chat_task}")

    try:
        stream = group_chat.run_stream(task=chat_task)
        await Console().run(stream)
        agentops.end_trace(tracer, end_state="Success")

    except Exception as e:
        print(f"An error occurred: {e}")
        agentops.end_trace(tracer, end_state="Error")
    finally:
        await model_client.close()

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
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import nest_asyncio

        nest_asyncio.apply()
        asyncio.run(main())
    else:
        asyncio.run(main())

# You can view data on this run at [app.agentops.ai](app.agentops.ai).
#
# The dashboard will display LLM events for each message sent by each agent, including those made by the human user.
