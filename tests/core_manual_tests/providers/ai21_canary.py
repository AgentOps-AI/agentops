import asyncio

import agentops
from dotenv import load_dotenv
import os
import ai21
from ai21.models.chat import ChatMessage

load_dotenv()
agentops.init(default_tags=["ai21-provider-test"])

api_key = os.getenv("AI2I_API_KEY")
ai21_client = ai21.AI21Client(api_key=api_key)
async_ai21_client = ai21.AsyncAI21Client(api_key=api_key)

messages = [
    ChatMessage(content="You are an expert mathematician.", role="system"),
    ChatMessage(
        content="Write a  summary of 5 lines on the Shockley diode equation.",
        role="user",
    ),
]

response = ai21_client.chat.completions.create(
    model="jamba-1.5-mini",
    messages=messages,
)


stream_response = ai21_client.chat.completions.create(
    model="jamba-1.5-mini",
    messages=messages,
    stream=True,
)

response = ""
for chunk in stream_response:
    response += chunk.choices[0].delta.content
print(response)


async def async_test():
    async_response = await async_ai21_client.chat.completions.create(
        model="jamba-1.5-mini",
        messages=messages,
    )
    print(async_response)


asyncio.run(async_test())

agentops.stop_instrumenting()

untracked_response = ai21_client.chat.completions.create(
    model="jamba-1.5-mini",
    messages=messages,
)


agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with one LLM event
###
