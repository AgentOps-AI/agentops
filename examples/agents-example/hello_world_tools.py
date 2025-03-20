# To run this file from project root: AGENTOPS_LOG_LEVEL=debug uv run examples/agents-example/hello_world_tools.py
import asyncio
from agents import Agent, Runner, function_tool
from dotenv import load_dotenv
import os

load_dotenv()

import agentops

@function_tool
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    # This is a mock function that would normally call a weather API
    return f"The weather in {location} is currently sunny and 72°F."

@function_tool
def calculate_tip(amount: float, percentage: float) -> str:
    """Calculate tip amount based on bill total and percentage."""
    tip = amount * (percentage / 100)
    total = amount + tip
    return f"For a ${amount:.2f} bill with {percentage}% tip: Tip amount is ${tip:.2f}, total bill is ${total:.2f}"

async def main():
    agentops.init()
    
    # Create agent with tools - use the decorated functions directly
    agent = Agent(
        name="Tool Demo Agent",
        instructions="You are a helpful assistant that can check weather and calculate tips.",
        tools=[get_weather, calculate_tip]
    )

    # Run agent with tools
    result = await Runner.run(agent, "What's the weather in Seattle? Also, calculate a 20% tip on a $85.75 bill.")
    print(result.final_output)
    
    # Print tool calls for debugging
    print("\nTool Calls Made:")
    for step in result.steps:
        if hasattr(step, 'tool_calls') and step.tool_calls:
            for tool_call in step.tool_calls:
                print(f"Tool: {tool_call.name}")
                print(f"Arguments: {tool_call.arguments}")
                print(f"Response: {tool_call.response}")
                print()

if __name__ == "__main__":
    asyncio.run(main())