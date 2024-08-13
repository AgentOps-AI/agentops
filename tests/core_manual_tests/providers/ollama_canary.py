import agentops
from dotenv import load_dotenv
import ollama

load_dotenv()
agentops.init(default_tags=["ollama-provider-test"])

response = ollama.chat(
    model="llama3.1",
    messages=[
        {
            "role": "user",
            "content": "Why is the sky blue?",
        },
    ],
)
print(response)
print(response["message"]["content"])

agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with one LLM event
###
