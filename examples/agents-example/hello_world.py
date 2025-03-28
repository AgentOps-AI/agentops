# To run this file from project root: AGENTOPS_LOG_LEVEL=debug uv run examples/agents-example/hello_world.py
import asyncio
from agents import Agent, Runner
from dotenv import load_dotenv
import os

load_dotenv()

import agentops

async def main():
    agentops.init(tags=["test", "openai-agents"])
    
    agent = Agent(
        name="Hello World Agent",
        instructions="You are a helpful assistant. Your task is to answer questions about programming concepts.",
    )

    # Regular agent run
    result = await Runner.run(agent, "Tell me about recursion in programming.")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())