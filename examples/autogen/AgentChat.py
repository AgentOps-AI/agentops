# Microsoft Autogen Multi-Agent Collaboration Example
#
# This example demonstrates AI-to-AI collaboration using multiple specialized agents working together without human interaction.
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

from autogen_agentchat.agents import AssistantAgent
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
agentops.init(auto_start_session=False, trace_name="Autogen Multi-Agent Collaboration Example")
tracer = agentops.start_trace(
    trace_name="Microsoft Multi-Agent Collaboration Example",
    tags=["autogen-collaboration", "microsoft-autogen", "agentops-example"],
)

# AutoGen will now start automatically tracking
#
# * LLM prompts and completions
# * Token usage and costs
# * Agent names and actions
# * Correspondence between agents
# * Tool usage
# * Errors
# # Multi-Agent Collaboration Example
# Define model and API key
model_name = "gpt-4o-mini"  # Or "gpt-4o" / "gpt-4o-mini" as per migration guide examples
api_key = os.getenv("OPENAI_API_KEY")

# Create the model client
model_client = OpenAIChatCompletionClient(model=model_name, api_key=api_key)

# Create multiple AI agents with different roles
research_agent = AssistantAgent(
    name="research_agent",
    system_message="You are a research specialist. Your role is to gather information, analyze data, and provide insights on topics. You ask thoughtful questions and provide well-researched responses.",
    model_client=model_client,
)

creative_agent = AssistantAgent(
    name="creative_agent",
    system_message="You are a creative strategist. Your role is to brainstorm innovative solutions, think outside the box, and propose creative approaches to problems. You build on others' ideas and suggest novel perspectives.",
    model_client=model_client,
)

analyst_agent = AssistantAgent(
    name="analyst_agent",
    system_message="You are a critical analyst. Your role is to evaluate ideas, identify strengths and weaknesses, and provide constructive feedback. You help refine concepts and ensure practical feasibility.",
    model_client=model_client,
)


async def main():
    # Set up a longer conversation to allow for meaningful AI-to-AI interaction
    termination = MaxMessageTermination(max_messages=8)

    group_chat = RoundRobinGroupChat(
        [research_agent, creative_agent, analyst_agent],  # AI agents working together
        termination_condition=termination,
    )

    # A task that will engage all three agents in meaningful collaboration
    chat_task = "Let's develop a comprehensive strategy for reducing plastic waste in urban environments. I need research on current methods, creative solutions, and analysis of feasibility."
    print(f"🎯 Task: {chat_task}")
    print("\n" + "=" * 80)
    print("🤖 AI Agents Collaboration Starting...")
    print("=" * 80)

    try:
        stream = group_chat.run_stream(task=chat_task)
        await Console(stream=stream)
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
# The dashboard will display LLM events for each message sent by each agent, showing the full AI-to-AI collaboration process with research, creative, and analytical perspectives.
