import asyncio

from openai.types.responses import ResponseTextDeltaEvent

from agents import Agent, Runner


from dotenv import load_dotenv
import os
import agentops

load_dotenv()

AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "your-api-key"
agentops.init(api_key=AGENTOPS_API_KEY)


async def main():
    agent = Agent(
        name="Joker",
        instructions="You are a helpful assistant.",
    )

    result = Runner.run_streamed(agent, input="Please tell me 5 jokes.")
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
