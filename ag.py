from typing import Annotated, Literal
from autogen import ConversableAgent, register_function
import agentops
import os
from dotenv import load_dotenv
from IPython.core.error import (
    StdinNotImplementedError,
)  # only needed by AgentOps testing automation
import time

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "<your_openai_key>"
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "<your_agentops_key>"

agentops.init(AGENTOPS_API_KEY, default_tags=["autogen-tool-example"])

print("AgentOps is now running. You can view your session in the link above")

# Define model, openai api key, tags, etc in the agent configuration
config_list = [
    {
        "model": "gpt-4o-mini",
        "api_key": OPENAI_API_KEY,
        "tags": ["mathagent-example", "tool"],
        "cache_seed": None,
    }
]

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


# Create the agent that uses the LLM.
assistant = ConversableAgent(
    name="Assistant",
    system_message="You are a helpful AI assistant. "
    "You can help with simple calculations. "
    "Return 'TERMINATE' when the task is done.",
    llm_config={"config_list": config_list},
)

# The user proxy agent is used for interacting with the assistant agent
# and executes tool calls.
user_proxy = ConversableAgent(
    name="User",
    llm_config=False,
    is_termination_msg=lambda msg: msg.get("content") is not None
    and "TERMINATE" in msg["content"],
    human_input_mode="NEVER",
)

assistant.register_for_llm(name="calculator", description="A simple calculator")(
    calculator
)
user_proxy.register_for_execution(name="calculator")(calculator)

# Register the calculator function to the two agents.
register_function(
    calculator,
    caller=assistant,  # The assistant agent can suggest calls to the calculator.
    executor=user_proxy,  # The user proxy agent can execute the calculator calls.
    name="calculator",  # By default, the function name is used as the tool name.
    description="A simple calculator",  # A description of the tool.
)

# Let the assistant start the conversation.  It will end when the user types "exit".
start_time = time.time()
try:
    user_proxy.initiate_chat(
        assistant, message="What is (1423 - 123) / 3 + (32 + 23) * 5?"
    )
except StdinNotImplementedError:
    # This is only necessary for AgentOps testing automation which is headless and will not have user input
    print("Stdin not implemented. Skipping initiate_chat")
    # agentops.end_session("Indeterminate")

end_time = time.time()
duration = end_time - start_time
print(f"The duration of this run was {duration:.2f} seconds")

# agentops.end_session("Success")
