import asyncio

import agentops
from dotenv import load_dotenv
import os
from mistralai import Mistral

load_dotenv()
agentops.init(default_tags=["mistral-provider-test"])
client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))


def run_asyncio_task(task_func):
    try:
        asyncio.run(task_func())
    except RuntimeError as e:
        if str(e) == "Event loop is closed":
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(task_func())
        else:
            raise


chat = client.chat.complete(
    model="open-mistral-nemo",
    messages=[
        {
            "role": "user",
            "content": "Say Hello",
        },
    ],
)


stream = client.chat.stream(
    model="open-mistral-nemo",
    messages=[
        {
            "role": "user",
            "content": "Say Hello 2",
        },
    ],
)

result = ""
for event in stream:
    if event.data.choices[0].finish_reason == "stop":
        print(result)
    else:
        result += event.data.choices[0].delta.content


async def async_chat_test():
    async_chat = await client.chat.complete_async(
        model="open-mistral-nemo",
        messages=[
            {
                "role": "user",
                "content": "Say Hello 3",
            },
        ],
    )
    print(async_chat)


# asyncio.run(async_chat_test())
run_asyncio_task(async_chat_test)


async def async_stream_test():
    async_stream = await client.chat.stream_async(
        model="open-mistral-nemo",
        messages=[
            {
                "role": "user",
                "content": "Say Hello 4",
            },
        ],
    )

    result = ""
    async for event in async_stream:
        if event.data.choices[0].finish_reason == "stop":
            print(result)
        else:
            result += event.data.choices[0].delta.content


# asyncio.run(async_stream_test())
run_asyncio_task(async_stream_test)

agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with two LLM events
###
