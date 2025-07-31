# AG2 Multi-Agent Group Chat Example with AgentOps Integration
#
# This script demonstrates how to orchestrate a group of specialized AI agents collaborating on a task using AG2 and AgentOps.
#
# Overview
# This example shows how to:
# 1. Initialize multiple AG2 agents with different roles (researcher, coder, critic, and user proxy)
# 2. Set up a group chat where agents interact and collaborate to solve a problem
# 3. Simulate a human participant using a user proxy agent
# 4. Limit the number of chat rounds and user turns for controlled execution
# 5. Track and monitor all agent interactions and LLM calls using AgentOps for full traceability
#
# By using group chat and specialized agents, you can model real-world collaborative workflows, automate complex problem solving, and analyze agent behavior in detail.

# %pip install agentops
# %pip install ag2
# %pip install nest-asyncio

import os
import agentops
import autogen

# Initialize AgentOps for tracing and monitoring
agentops.init(auto_start_session=False, trace_name="AG2 Group Chat")
tracer = agentops.start_trace(trace_name="AG2 Group Chat", tags=["ag2-group-chat", "agentops-example"])

# Configure your AG2 agents with model and API key
config_list = [
    {
        "model": "gpt-4",
        "api_key": os.getenv("OPENAI_API_KEY"),
    }
]
llm_config = {
    "config_list": config_list,
    "timeout": 60,
}

# Create a team of agents with specialized roles
researcher = autogen.AssistantAgent(
    name="researcher",
    llm_config=llm_config,
    system_message="You are a researcher who specializes in finding accurate information.",
)
coder = autogen.AssistantAgent(
    name="coder", llm_config=llm_config, system_message="You are an expert programmer who writes clean, efficient code."
)
critic = autogen.AssistantAgent(
    name="critic", llm_config=llm_config, system_message="You review solutions and provide constructive feedback."
)

# The user proxy agent simulates a human participant in the chat
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="TERMINATE",  # Stops when a message ends with 'TERMINATE'
    max_consecutive_auto_reply=10,  # Limits auto-replies before requiring termination
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={"last_n_messages": 3, "work_dir": "coding"},
)
# Create a group chat with all agents and set a maximum number of rounds
groupchat = autogen.GroupChat(
    agents=[user_proxy, researcher, coder, critic],
    messages=[],
    max_round=4,  # Limits the total number of chat rounds
)
# The manager coordinates the group chat and LLM configuration
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)
# Start the group chat with an initial task and a maximum number of user turns
user_proxy.initiate_chat(
    manager,
    message="Create a Python program to analyze sentiment from Twitter data.",
    max_turns=2,  # Limits the number of user turns
)
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
