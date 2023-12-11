from openai.resources.chat import completions
import openai
from openai import OpenAI, AsyncOpenAI
import agentops
import asyncio
from dotenv import load_dotenv
load_dotenv()
client = OpenAI()


async_client = AsyncOpenAI()


# completions.Completions.create = lambda *args, **kwargs: print('test2')

print('Running OpenAI v1.0.0+')


# Assuming that instantiating agentops.Client will trigger the LlmTracker to override methods
ao_client = agentops.Client(tags=['mock agent'])


# Now the client.chat.completions.create should be the overridden method
# chat_completion = client.chat.completions.create(
#     messages=[
#         {
#             "role": "user",
#             "content": "Say this is a test",
#         }
#     ],
#     model="gpt-3.5-turbo",
# )

# Test the async version of client.chat.completions.create


async def test_async_chat_completion():
    return await async_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Say this is a test",
            }
        ],
        model="gpt-3.5-turbo",
    )


asyncio.run(test_async_chat_completion())

ao_client.end_session('Success')
