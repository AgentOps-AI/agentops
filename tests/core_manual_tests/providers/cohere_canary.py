import agentops
from dotenv import load_dotenv
import os
import cohere

load_dotenv()
agentops.init(default_tags=["cohere-provider-test"])
co = cohere.Client()

chat = co.chat(message="Tell me a fun fact about potatoes")

stream = co.chat_stream(message="Tell me a fun fact about radishes")

response = ""
for event in stream:
    if event.event_type == "text-generation":
        response += event.text
        print(event.text, end="")
    elif event.event_type == "stream-end":
        print("\n")
        print(event)
        print("\n")


agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with one LLM event
###
