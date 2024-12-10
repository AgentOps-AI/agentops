import agentops
import asyncio
import os
from dotenv import load_dotenv

from llama_stack_client import LlamaStackClient
from llama_stack_client.lib.agents.agent import Agent
from llama_stack_client.lib.agents.event_logger import EventLogger
from llama_stack_client.types.agent_create_params import AgentConfig

load_dotenv()

agentops.init(os.getenv("AGENTOPS_API_KEY"), default_tags=["llama-stack-client-example"], auto_start_session=False)

LLAMA_STACK_HOST = "0.0.0.0"
LLAMA_STACK_PORT = 5001
INFERENCE_MODEL = "meta-llama/Llama-3.2-1B-Instruct"


async def agent_test():
    client = LlamaStackClient(
        base_url=f"http://{LLAMA_STACK_HOST}:{LLAMA_STACK_PORT}",
    )

    available_shields = [shield.identifier for shield in client.shields.list()]
    if not available_shields:
        print("No available shields. Disable safety.")
    else:
        print(f"Available shields found: {available_shields}")
    available_models = [model.identifier for model in client.models.list()]
    if not available_models:
        raise ValueError("No available models")
    else:
        selected_model = available_models[0]
        print(f"Using model: {selected_model}")

    agent_config = AgentConfig(
        model=selected_model,
        instructions="You are a helpful assistant. Just say hello as a greeting.",
        sampling_params={
            "strategy": "greedy",
            "temperature": 1.0,
            "top_p": 0.9,
        },
        tools=[
            {
                "type": "brave_search",
                "engine": "brave",
                "api_key": os.getenv("BRAVE_SEARCH_API_KEY"),
            }
        ],
        tool_choice="auto",
        tool_prompt_format="json",
        input_shields=available_shields if available_shields else [],
        output_shields=available_shields if available_shields else [],
        enable_session_persistence=False,
    )
    agent = Agent(client, agent_config)
    user_prompts = [
        "Hello",
        "Which players played in the winning team of the NBA western conference semifinals of 2014, please use tools",
    ]

    session_id = agent.create_session("test-session")

    for prompt in user_prompts:
        response = agent.create_turn(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            session_id=session_id,
        )

        for log in EventLogger().log(response):
            log.print()


agentops.start_session()
asyncio.run(agent_test())
agentops.end_session(end_state="Success")
