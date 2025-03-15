# To run this file from project root: AGENTOPS_LOG_LEVEL=debug uv run python examples/agents-examples/basic/hello_world.py
import asyncio

from agents import Agent, Runner

from dotenv import load_dotenv
import os
import agentops

load_dotenv()

AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "your-api-key"
agentops.init(api_key=AGENTOPS_API_KEY)


async def main():
    agent = Agent(
        name="Assistant",
        instructions="You only respond in haikus.",
    )

    result = await Runner.run(agent, "Tell me about recursion in programming.")
    print(result.final_output)
    # Function calls itself,
    # Looping in smaller pieces,
    # Endless by design.


if __name__ == "__main__":
    asyncio.run(main())
