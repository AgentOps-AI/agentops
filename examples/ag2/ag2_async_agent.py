# AG2 Async Agent Chat with Automated Responses
#
# This notebook demonstrates how to leverage asynchronous programming with AG2 agents
# to create automated conversations between AI agents, eliminating the need for human
# input while maintaining full traceability.
#
# Overview
# This notebook demonstrates a practical example of automated AI-to-AI communication where we:
#
# 1. Initialize AG2 agents with OpenAI's GPT-4o-mini model
# 2. Create custom async agents that simulate human-like responses and processing delays
# 3. Automate the entire conversation flow without requiring manual intervention
# 4. Track all interactions using AgentOps for monitoring and analysis
#
# By using async operations and automated responses, you can create fully autonomous
# agent conversations that simulate real-world scenarios. This is particularly useful
# for testing, prototyping, and creating demos where you want to showcase agent
# capabilities without manual input.

# %pip install agentops
# %pip install ag2
# %pip install nest-asyncio

import asyncio
from typing import Dict, Optional, Union
import os
from dotenv import load_dotenv
import nest_asyncio
import agentops
from autogen import AssistantAgent
from autogen.agentchat.user_proxy_agent import UserProxyAgent

# Load environment variables for API keys
load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
# Initialize AgentOps for tracking and monitoring
agentops.init(auto_start_session=False, trace_name="AG2 Async Demo")
tracer = agentops.start_trace(trace_name="AG2 Async Agent Demo", tags=["ag2-async-demo", "agentops-example"])


# Define an asynchronous function that simulates async processing
async def simulate_async_processing(task_name: str, delay: float = 1.0) -> str:
    """
    Simulate some asynchronous processing (e.g., API calls, file operations, etc.)
    """
    print(f"🔄 Starting async task: {task_name}")
    await asyncio.sleep(delay)  # Simulate async work
    print(f"✅ Completed async task: {task_name}")
    return f"Processed: {task_name}"


# Define a custom UserProxyAgent that simulates automated user responses
class AutomatedUserProxyAgent(UserProxyAgent):
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        self.response_count = 0
        self.predefined_responses = [
            "Yes, please generate interview questions for these topics.",
            "The questions look good. Can you make them more specific to senior-level positions?",
            "Perfect! These questions are exactly what we need. Thank you!",
        ]

    async def a_get_human_input(self, prompt: str) -> str:
        # Simulate async processing before responding
        await simulate_async_processing(f"Processing user input #{self.response_count + 1}")

        if self.response_count < len(self.predefined_responses):
            response = self.predefined_responses[self.response_count]
            self.response_count += 1
            print(f"👤 User: {response}")
            return response
        else:
            print("👤 User: TERMINATE")
            return "TERMINATE"

    async def a_receive(
        self,
        message: Union[Dict, str],
        sender,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        await super().a_receive(message, sender, request_reply, silent)


# Define an AssistantAgent that simulates async processing before responding
class AsyncAssistantAgent(AssistantAgent):
    async def a_receive(
        self,
        message: Union[Dict, str],
        sender,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        # Simulate async processing before responding
        await simulate_async_processing("Analyzing request and preparing response", 0.5)
        await super().a_receive(message, sender, request_reply, silent)


async def main():
    print("🚀 Starting AG2 Async Demo")

    # Create agents with automated behavior
    user_proxy = AutomatedUserProxyAgent(
        name="hiring_manager",
        human_input_mode="NEVER",  # No human input required
        max_consecutive_auto_reply=3,
        code_execution_config=False,
        is_termination_msg=lambda msg: "TERMINATE" in str(msg.get("content", "")),
    )

    assistant = AsyncAssistantAgent(
        name="interview_consultant",
        system_message="""You are an expert interview consultant. When given interview topics, 
        you create thoughtful, relevant questions. You ask for feedback and incorporate it.
        When the user is satisfied with the questions, end with 'TERMINATE'.""",
        llm_config={"config_list": [{"model": "gpt-4o-mini", "api_key": os.environ.get("OPENAI_API_KEY")}]},
        is_termination_msg=lambda msg: "TERMINATE" in str(msg.get("content", "")),
    )

    try:
        print("🤖 Initiating automated conversation...")
        # Start the automated chat between the user and assistant
        await user_proxy.a_initiate_chat(
            assistant,
            message="""I need help creating interview questions for these topics:
            - Resume Review
            - Technical Skills Assessment  
            - Project Discussion
            - Job Role Expectations
            - Closing Remarks
            
            Please create 2-3 questions for each topic.""",
            max_turns=6,
        )

        # Let's check programmatically that spans were recorded in AgentOps
        print("\n" + "=" * 50)
        print("Now let's verify that our LLM calls were tracked properly...")
        try:
            agentops.validate_trace_spans(trace_context=tracer)
            print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
        except agentops.ValidationError as e:
            print(f"\n❌ Error validating spans: {e}")
            raise

    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
    finally:
        agentops.end_trace(tracer, end_state="Success")

    print("\n🎉 Demo completed successfully!")


# Run the main async demo
nest_asyncio.apply()
asyncio.run(main())
