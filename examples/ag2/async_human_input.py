# Agent Chat with Async Human Inputs
#
# We are going to create an agent that can chat with a human asynchronously. The agent will be able to respond to messages from the human and will also be able to send messages to the human.
#
# We are going to use AgentOps to monitor the agent's performance and observe its interactions with the human.
# # Install required dependencies
# %pip install agentops
# %pip install ag2
# %pip install chromadb
# %pip install sentence_transformers
# %pip install tiktoken
# %pip install pypdf
# %pip install nest-asyncio
import asyncio
from typing import Dict, Optional, Union
import os
from dotenv import load_dotenv

import nest_asyncio
import agentops
from autogen import AssistantAgent
from autogen.agentchat.user_proxy_agent import UserProxyAgent

load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

agentops.init(auto_start_session=False, trace_name="AG2 Async Human Input")
tracer = agentops.start_trace(
    trace_name="AG2 Agent chat with Async Human Inputs", tags=["ag2-chat-async-human-inputs", "agentops-example"]
)


# Define an asynchronous function that simulates some asynchronous task (e.g., I/O operation)
async def my_asynchronous_function():
    print("Start asynchronous function")
    await asyncio.sleep(2)  # Simulate some asynchronous task (e.g., I/O operation)
    print("End asynchronous function")
    return "input"


# Define a custom class `CustomisedUserProxyAgent` that extends `UserProxyAgent`
class CustomisedUserProxyAgent(UserProxyAgent):
    # Asynchronous function to get human input
    async def a_get_human_input(self, prompt: str) -> str:
        # Call the asynchronous function to get user input asynchronously
        user_input = await my_asynchronous_function()
        return user_input

    # Asynchronous function to receive a message
    async def a_receive(
        self,
        message: Union[Dict, str],
        sender,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        # Call the superclass method to handle message reception asynchronously
        await super().a_receive(message, sender, request_reply, silent)


class CustomisedAssistantAgent(AssistantAgent):
    # Asynchronous function to get human input
    async def a_get_human_input(self, prompt: str) -> str:
        # Call the asynchronous function to get user input asynchronously
        user_input = await my_asynchronous_function()
        return user_input

    # Asynchronous function to receive a message
    async def a_receive(
        self,
        message: Union[Dict, str],
        sender,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        # Call the superclass method to handle message reception asynchronously
        await super().a_receive(message, sender, request_reply, silent)


nest_asyncio.apply()


async def main():
    boss = CustomisedUserProxyAgent(
        name="boss",
        human_input_mode="ALWAYS",
        max_consecutive_auto_reply=0,
        code_execution_config=False,
    )

    assistant = CustomisedAssistantAgent(
        name="assistant",
        system_message="You will provide some agenda, and I will create questions for an interview meeting. Every time when you generate question then you have to ask user for feedback and if user provides the feedback then you have to incorporate that feedback and generate new set of questions and if user don't want to update then terminate the process and exit",
        llm_config={"config_list": [{"model": "gpt-4o-mini", "api_key": os.environ.get("OPENAI_API_KEY")}]},
    )

    await boss.a_initiate_chat(
        assistant,
        message="Resume Review, Technical Skills Assessment, Project Discussion, Job Role Expectations, Closing Remarks.",
        n_results=3,
    )


# await main()
agentops.end_trace(tracer, end_state="Success")

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=tracer)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise
