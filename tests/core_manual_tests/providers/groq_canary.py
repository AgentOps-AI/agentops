import asyncio

import agentops
from dotenv import load_dotenv
import os
from groq import Groq, AsyncGroq

load_dotenv()
agentops.init(default_tags=["groq-provider-test"])
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
async_groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

messages = [{"role": "user", "content": "Hello"}]

# option 1: use session.patch
res = groq_client.chat.completions.create(
    model="llama3-70b-8192",
    messages=[
        {"role": "user", "content": "Say hello"},
    ],
)

stream_res = groq_client.chat.completions.create(
    model="llama3-70b-8192",
    messages=[
        {"role": "user", "content": "Say hello"},
    ],
    stream=True,
)

for chunk in stream_res:
    print(chunk)


async def async_test():
    async_res = await async_groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "user", "content": "Say hello"},
        ],
    )
    print(async_res)


asyncio.run(async_test())

agentops.stop_instrumenting()

untracked_res = groq_client.chat.completions.create(
    model="llama3-70b-8192",
    messages=[
        {"role": "user", "content": "Say hello"},
    ],
)

agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with one LLM event
###
