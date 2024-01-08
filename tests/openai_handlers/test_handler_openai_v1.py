import time
from openai.resources.chat import completions
import openai
from openai import OpenAI, AsyncOpenAI
import agentops
import asyncio
from dotenv import load_dotenv
load_dotenv()
client = OpenAI()


async_client = AsyncOpenAI()


print('Running OpenAI v1.0.0+')


# Assuming that instantiating agentops.Client will trigger the LlmTracker to override methods
ao_client = agentops.Client(tags=['mock agent', openai.__version__])


# Now the client.chat.completions.create should be the overridden method
print('Chat completion')
chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Say this is a test",
        }
    ],
    model="gpt-3.5-turbo",
)

# test streaming
print('Chat completion streaming')
chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Say this is a test",
        }
    ],
    model="gpt-3.5-turbo",
    stream=True
)
start_time = time.time()

collected_chunks = []
collected_messages = []

print(chat_completion)

for chunk in chat_completion:
    chunk_time = time.time() - start_time  # calculate the time delay of the chunk
    collected_chunks.append(chunk)  # save the event response
    chunk_message = chunk.choices[0].delta.content  # extract the message
    collected_messages.append(chunk_message)  # save the message
    # print the delay and text
    print(
        f"Message received {chunk_time:.2f} seconds after request: {chunk_message}")


# # Test the async version of client.chat.completions.create

async def test_async_chat_completion():
    return await async_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Say this is an async test",
            }
        ],
        model="gpt-3.5-turbo",
    )


async def test_async_chat_completion_stream():
    chat_completion_stream = await async_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Say this is an async test",
            }
        ],
        model="gpt-3.5-turbo",
        stream=True
    )
    async for chunk in chat_completion_stream:
        print(chunk)


print('Running async tests')
asyncio.run(test_async_chat_completion())
print('Running async streaming test')
asyncio.run(test_async_chat_completion_stream())

ao_client.end_session('Success')
