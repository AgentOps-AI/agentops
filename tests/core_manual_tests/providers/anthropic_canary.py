import asyncio

import agentops
from dotenv import load_dotenv
import anthropic

load_dotenv()
agentops.init(default_tags=["anthropic-provider-test"])
anthropic_client = anthropic.Anthropic()
async_anthropic_client = anthropic.AsyncAnthropic()

# Test 1: Basic non-streaming response
response = anthropic_client.messages.create(
    max_tokens=1024,
    model="claude-3-sonnet-20240229",
    messages=[
        {
            "role": "user",
            "content": "say hi",
        }
    ],
)

# Test 2: Legacy streaming pattern
stream_response = anthropic_client.messages.create(
    max_tokens=1024,
    model="claude-3-sonnet-20240229",
    messages=[
        {
            "role": "user",
            "content": "say hi 2",
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

# Test 3: Sync context handler streaming pattern
with anthropic_client.messages.create(
    max_tokens=1024,
    model="claude-3-sonnet-20240229",
    messages=[
        {
            "role": "user",
            "content": "say hi with context handler",
        }
    ],
    stream=True,
) as stream:
    response = ""
    for text in stream.text_stream:
        response += text
    print(response)


# Test 4: Async response and streaming patterns
async def async_test():
    # Test 4.1: Basic async response
    async_response = await async_anthropic_client.messages.create(
        max_tokens=1024,
        model="claude-3-sonnet-20240229",
        messages=[
            {
                "role": "user",
                "content": "say hi 3",
            }
        ],
    )
    print(async_response)

    # Test 4.2: Async context handler streaming pattern
    async with async_anthropic_client.messages.create(
        max_tokens=1024,
        model="claude-3-sonnet-20240229",
        messages=[
            {
                "role": "user",
                "content": "say hi with async context handler",
            }
        ],
        stream=True,
    ) as stream:
        response = ""
        async for text in stream.text_stream:
            response += text
        print(response)


# Run async tests
asyncio.run(async_test())

# Test 5: Verify instrumentation can be disabled
agentops.stop_instrumenting()

untracked_response = anthropic_client.messages.create(
    max_tokens=1024,
    model="claude-3-sonnet-20240229",
    messages=[
        {
            "role": "user",
            "content": "say hi 4",
        }
    ],
)

# End session
agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with one LLM event
###
