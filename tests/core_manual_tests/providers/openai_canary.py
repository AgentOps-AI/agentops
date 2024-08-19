import agentops
import asyncio
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
from agentops import ActionEvent

load_dotenv()
agentops.init(default_tags=["openai-v1-provider-test"])
openai = OpenAI()
async_openai = OpenAI()


# option 1: use session.patch
response = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.5,
)

stream_response = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello streamed"}],
    temperature=0.5,
    stream=True,
)

for chunk in stream_response:
    print(chunk)

async_response = async_openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello async"}],
    temperature=0.5,
)

agentops.stop_instrumenting()

not_tracked_response = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello untracked"}],
    temperature=0.5,
)

agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with two LLM events
###
