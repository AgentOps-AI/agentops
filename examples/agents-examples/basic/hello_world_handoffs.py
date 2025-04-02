# To run this file from project root: AGENTOPS_LOG_LEVEL=debug uv run examples/agents-example/hello_world_handoffs.py
import asyncio
from agents import Agent, Runner
from dotenv import load_dotenv
import os

load_dotenv()

import agentops

async def main():
    agentops.init()
    
    # Define a secondary agent that specializes in math
    math_agent = Agent(
        name="Math Expert",
        model="o3-mini",
        instructions="You are a mathematics expert. Your task is to answer questions specifically about math concepts.",
        handoff_description="A specialized agent for answering mathematical questions."
    )
    
    # Configure the primary agent with handoffs to the math agent
    primary_agent_with_handoffs = Agent(
        name="Programming Agent",
        instructions="You are a programming expert. Your task is to answer questions about programming concepts. If a user asks about math concepts, hand off to the Math Expert agent.",
        handoffs=[math_agent, ]
    )
    
    result = await Runner.run(primary_agent_with_handoffs, "Tell me about recursion in programming.")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())