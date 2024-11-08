import autogen
import agentops
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv
from agentops import ActionEvent
from openai import OpenAI
import os
from autogen import ConversableAgent, UserProxyAgent
import os
from dotenv import load_dotenv
from IPython.core.error import (
    StdinNotImplementedError,
)  # only needed by AgentOps testing automation
from typing import Annotated, Literal
from autogen import register_function
import time
import litellm

load_dotenv()

agentops.init(auto_start_session=False)
client = OpenAI()
app = FastAPI()


@app.get("/completion")
def completion():
    start_time = time.time()

    session_start = time.time()
    session = agentops.start_session(tags=["api-server-test", "fastapi"])
    session_time = time.time() - session_start
    print(f"Session initialization took {session_time:.2f} seconds")

    messages = [{"role": "user", "content": "Hello"}]

    llm_start = time.time()
    response = litellm.completion(
        model="gpt-4o",
        messages=messages,
        temperature=0.5,
    )
    print(response)
    llm_time = time.time() - llm_start
    print(f"LLM call took {llm_time:.2f} seconds")

    record_start = time.time()
    session.record(
        ActionEvent(
            action_type="Agent says hello",
            params=messages,
            returns=str(response.choices[0].message.content),
        ),
    )
    record_time = time.time() - record_start
    print(f"Recording event took {record_time:.2f} seconds")

    end_start = time.time()
    session.end_session(end_state="Success")
    end_time = time.time() - end_start
    print(f"Ending session took {end_time:.2f} seconds")

    total_time = time.time() - start_time
    print(f"Total completion time: {total_time:.2f} seconds")

    return {"response": response}


@app.get("/autogen_completion")
def autogen_completion():
    # Add time tracking
    start_time = time.time()
    # Record start time for session initialization
    session_start = time.time()
    session = agentops.start_session(tags=["api-server-test", "fastapi", "autogen"])
    session_time = time.time() - session_start
    print(f"Session initialization took {session_time:.2f} seconds")

    # Define model, openai api key, tags, etc in the agent configuration
    config_list = [
        {
            "model": "gpt-4o-mini",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "tags": ["mathagent-example", "tool"],
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

    # Create the agent that uses the LLM
    assistant = ConversableAgent(
        name="Assistant",
        system_message="You are a helpful AI assistant. "
        "You can help with simple calculations. "
        "Return 'TERMINATE' when the task is done.",
        llm_config={"config_list": config_list},
    )

    # Create the user proxy agent
    user_proxy = ConversableAgent(
        name="User",
        llm_config=False,
        is_termination_msg=lambda msg: msg.get("content") is not None
        and "TERMINATE" in msg["content"],
        human_input_mode="NEVER",
    )

    # Register the calculator function
    assistant.register_for_llm(name="calculator", description="A simple calculator")(calculator)
    user_proxy.register_for_execution(name="calculator")(calculator)

    register_function(
        calculator,
        caller=assistant,
        executor=user_proxy,
        name="calculator",
        description="A simple calculator",
    )

    response = None
    try:
        response = user_proxy.initiate_chat(
            assistant, message="What is (1423 - 123) / 3 + (32 + 23) * 5?"
        )
    except StdinNotImplementedError:
        print("Stdin not implemented. Skipping initiate_chat")
        session.end_session("Indeterminate")
        return {"response": "Chat initiation skipped - stdin not implemented"}

    # Close your AgentOps session to indicate that it completed
    end_start = time.time()
    session.end_session("Success")
    end_duration = time.time() - end_start
    print(f"Session ended in {end_duration:.2f}s. Visit your AgentOps dashboard to see the replay")

    # Calculate duration at the end
    duration = time.time() - start_time
    print(f"Total duration: {duration:.2f} seconds")

    return {"response": response, "duration": duration}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=9696, reload=True)
