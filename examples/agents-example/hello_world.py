import asyncio
from dotenv import load_dotenv
from agents import Agent, Runner

load_dotenv()

import agentops

async def main():
    agentops.init()
    
    agent = Agent(
        name="Hello World Agent",
        instructions="You are a helpful assistant. Your task is to answer questions about programming concepts.",
    )

    result = await Runner.run(agent, "Tell me about recursion in programming.")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
