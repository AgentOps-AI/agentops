import asyncio

import agentops
from dotenv import load_dotenv
import cohere

load_dotenv()
agentops.init(default_tags=["cohere-provider-test"])
co = cohere.Client()
aco = cohere.AsyncClient()

chat = co.chat(message="say hi 1")

stream = co.chat_stream(message="say hi 2")
response = ""
for event in stream:
    if event.event_type == "text-generation":
        response += event.text
        print(event.text, end="")
    elif event.event_type == "stream-end":
        print("\n")
        print(event)
        print("\n")


async def main():
    async_response = await aco.chat(message="say hi 3")
    print(async_response)


asyncio.run(main())

agentops.stop_instrumenting()

# for cohere, because the client is not a singleton, calling `stop_instrumenting()` only affects
# new clients created, not existing clients.

co_untracked = cohere.Client()
chat_untracked = co_untracked.chat(message="say hi untracked")

agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with one LLM event
###
