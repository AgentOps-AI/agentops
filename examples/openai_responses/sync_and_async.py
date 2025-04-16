# To run this file from project root: AGENTOPS_LOG_LEVEL=debug uv run examples/openai_responses/sync_and_async.py
import asyncio
from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI, AsyncOpenAI
import agentops


def sync_responses_request():
    client = OpenAI()
    response = client.responses.create(
        model="gpt-4o",
        input="Explain the concept of synchronous Python in one sentence.",
    )
    return response


async def async_responses_request():
    client = AsyncOpenAI()
    response = await client.responses.create(
        model="gpt-4o",
        input="Explain the concept of async/await in Python in one sentence.",
        stream=False, 
    )
    return response


async def main():
    agentops.init()
    
    # Synchronous request
    sync_response = sync_responses_request()
    print(f"Synchronous Response:\n {sync_response.output_text}")
    
    # Asynchronous request
    async_response = await async_responses_request()
    print(f"Asynchronous Response:\n {async_response.output_text}")


if __name__ == "__main__":
    asyncio.run(main())