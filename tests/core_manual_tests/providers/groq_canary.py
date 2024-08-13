import agentops
from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()
agentops.init(default_tags=["groq-provider-test"])
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

messages = [{"role": "user", "content": "Hello"}]

# option 1: use session.patch
res = groq_client.chat.completions.create(
    model="llama3-70b-8192",
    messages=[
        {"role": "system", "content": "You are not a tracked agent"},
        {"role": "user", "content": "Say hello"},
    ],
)

agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with one LLM event
###
