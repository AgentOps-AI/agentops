from openai import AsyncOpenAI
import asyncio
import agentops
from agentops import record_action
from dotenv import load_dotenv

load_dotenv()

agentops.init()


@record_action("openai v1 async no streaming")
async def call_openai_v1_async_no_streaming():
    client = AsyncOpenAI()

    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert haiku writer"},
            {"role": "user", "content": "write me a haiku about devops"},
        ],
    )

    print(chat_completion)
    # raise ValueError("This is an intentional error for testing.")


@record_action("openai v1 async with streaming")
async def call_openai_v1_async_streaming():
    client = AsyncOpenAI()  # Using the async client

    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert haiku writer"},
            {"role": "user", "content": "write me a haiku about devops"},
        ],
        stream=True,
    )

    async for chunk in chat_completion:
        chunk_message = chunk.choices[0].delta.content
        print(chunk_message)
    # raise ValueError("This is an intentional error for testing.")


async def main():
    await call_openai_v1_async_no_streaming()
    await call_openai_v1_async_streaming()
    agentops.end_session(
        "Success"
    )  # This would also need to be made async if it makes network calls


asyncio.run(main())
