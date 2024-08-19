import asyncio

import agentops
from dotenv import load_dotenv
import os
import anthropic

load_dotenv()
agentops.init(default_tags=["anthropic-provider-test"])
anthropic_client = anthropic.Anthropic()
async_anthropic_client = anthropic.AsyncAnthropic()

response = anthropic_client.messages.create(
    max_tokens=1024,
    model="claude-3-5-sonnet-20240620",
    messages=[
        {
            "role": "user",
            "content": "What is 2+2?",
        }
    ],
)


stream_response = anthropic_client.messages.create(
    max_tokens=1024,
    model="claude-3-5-sonnet-20240620",
    messages=[
        {
            "role": "user",
            "content": "What is 2+2?",
        }
    ],
    stream=True,
)

response = ""
for event in stream_response:
    if event.type == "content_block_delta":
        response += event.delta.text
    elif event.type == "message_stop":
        print(response)


async def async_test():
    async_response = await async_anthropic_client.messages.create(
        max_tokens=1024,
        model="claude-3-5-sonnet-20240620",
        messages=[
            {
                "role": "user",
                "content": "What is 2+2?",
            }
        ],
    )
    print(async_response)


asyncio.run(async_test())

agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with one LLM event
###
