import asyncio

import agentops
import os
from dotenv import load_dotenv
from mistralai import Mistral

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

agentops.init(default_tags=["mistral-provider-test"])
client = Mistral(MISTRAL_API_KEY)

response = client.chat.complete(
    model="open-mistral-nemo",
    messages=[
        {
            "role": "user",
            "content": "Say Hello",
        },
    ],
)


stream_response = client.chat.stream(
    model="open-mistral-nemo",
    messages=[
        {
            "role": "user",
            "content": "Say Hello again",
        }
    ],
)

response = ""
for event in stream_response:
    if event.data.choices[0].finish_reason == "stop":
        print(response)
    else:
        response += event.data.choices[0].delta.content


async def async_test():
    async_response = await client.chat.complete_async(
        model="open-mistral-nemo",
        messages=[
            {
                "role": "user",
                "content": "Say Hello in the Hindi language",
            }
        ],
    )
    print(async_response.choices[0].message.content)


async def async_stream_test():
    async_stream_response = await client.chat.stream_async(
        model="open-mistral-nemo",
        messages=[
            {
                "role": "user",
                "content": "Say Hello in the Japanese language",
            }
        ],
    )

    response = ""
    async for event in async_stream_response:
        if event.data.choices[0].finish_reason == "stop":
            print(response)
        else:
            response += event.data.choices[0].delta.content


async def main():
    await async_test()
    await async_stream_test()


asyncio.run(main())

agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with one LLM event
###
