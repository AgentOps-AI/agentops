import asyncio

import agentops
from dotenv import load_dotenv
import litellm

load_dotenv()
agentops.init(default_tags=["litellm-provider-test"])

# Test: chat completion (ModelResponse format)
response = litellm.completion(model="gpt-3.5-turbo", messages=[{"content": "Hello, how are you?", "role": "user"}])

# Test: responses API (ResponsesAPIResponse format)
# Note: litellm.responses() returns ResponsesAPIResponse objects which have
# a ``output`` field instead of ``choices`` and usage with ``input_tokens``/
# ``output_tokens`` instead of ``prompt_tokens``/``completion_tokens``.
# This exercises the LiteLLM Responses API attribute extraction path.

stream_response = litellm.completion(
    model="gpt-3.5-turbo",
    messages=[{"content": "Hello, how are you?", "role": "user"}],
    stream=True,
)
print(stream_response)
for chunk in stream_response:
    print(chunk)


async def main():
    async_response = await litellm.acompletion(
        model="gpt-3.5-turbo",
        messages=[{"content": "Hello, how are you?", "role": "user"}],
    )
    print(async_response)


asyncio.run(main())

agentops.stop_instrumenting()

untracked_response = litellm.completion(
    model="gpt-3.5-turbo", messages=[{"content": "Hello, how are you?", "role": "user"}]
)

agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with one LLM event
###
