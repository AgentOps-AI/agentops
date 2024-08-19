import asyncio

import agentops
from dotenv import load_dotenv
import ollama
from ollama import AsyncClient

load_dotenv()
agentops.init(default_tags=["ollama-provider-test"])

response = ollama.chat(
    model="llama3.1",
    messages=[
        {
            "role": "user",
            "content": "say hello sync",
        },
    ],
)

stream_response = ollama.chat(
    model="llama3.1",
    messages=[
        {
            "role": "user",
            "content": "say hello str",
        },
    ],
    stream=True,
)
for chunk in stream_response:
    print(chunk)


async def main():
    message = {"role": "user", "content": "say hello mr. async"}
    async_response = await AsyncClient().chat(model="llama3.1", messages=[message])


asyncio.run(main())

agentops.stop_instrumenting()

untracked_response = ollama.chat(
    model="llama3.1",
    messages=[
        {
            "role": "user",
            "content": "say hello",
        },
    ],
)

agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with one LLM event
###
