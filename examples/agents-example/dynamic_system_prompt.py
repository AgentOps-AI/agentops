import asyncio
import random
from typing import Literal
import os
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY") or "your-openai-api-key"
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY") or "your-agentops-api-key"
import agentops
agentops.init(
    instrument_llm_calls=True,
    log_level="DEBUG",
)
session = agentops.start_session(tags=["math-agent-test", "otel-semantic-conventions"])
from agents import Agent, RunContextWrapper, Runner


class CustomContext:
    def __init__(self, style: Literal["haiku", "pirate", "robot"]):
        self.style = style


def custom_instructions(
    agent: Agent[CustomContext], run_context: RunContextWrapper[CustomContext]
) -> str:
    context = run_context.context
    if context.style == "haiku":
        return "Only respond in haikus."
    elif context.style == "pirate":
        return "Respond as a pirate."
    else:
        return "Respond as a robot and say 'beep boop' a lot."


agent = Agent(
    name="Chat agent",
    instructions=custom_instructions,
)


async def main():
    choice: Literal["haiku", "pirate", "robot"] = random.choice(["haiku", "pirate", "robot"])
    context = CustomContext(style=choice)
    print(f"Using style: {choice}\n")

    user_message = "Tell me a joke."
    print(f"User: {user_message}")
    output = await Runner.run(agent, user_message, context=context)

    print(f"Assistant: {output.final_output}")


if __name__ == "__main__":
    asyncio.run(main())

"""
$ python examples/basic/dynamic_system_prompt.py

Using style: haiku

User: Tell me a joke.
Assistant: Why don't eggs tell jokes?
They might crack each other's shells,
leaving yolk on face.

$ python examples/basic/dynamic_system_prompt.py
Using style: robot

User: Tell me a joke.
Assistant: Beep boop! Why was the robot so bad at soccer? Beep boop... because it kept kicking up a debug! Beep boop!

$ python examples/basic/dynamic_system_prompt.py
Using style: pirate

User: Tell me a joke.
Assistant: Why did the pirate go to school?

To improve his arrr-ticulation! Har har har! 🏴‍☠️
"""
