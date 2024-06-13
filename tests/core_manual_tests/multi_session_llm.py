import agentops
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
agentops.init()
openai = OpenAI()

session_id_1 = agentops.start_session(tags=["multi-session-test-1"])
session_id_2 = agentops.start_session(tags=["multi-session-test-2"])

messages = [{"role": "user", "content": "Hello"}]

response = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=messages,
    temperature=0.5,
    session_id=session_id_1,  # <-- add the agentops session_id to the create function
)

response = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=messages,
    temperature=0.5,
    session_id=session_id_2,  # <-- add the agentops session_id to the create function
)

agentops.end_session(end_state="Success", session_id=session_id_1)
agentops.end_session(end_state="Success", session_id=session_id_2)

###
#  Used to verify that two sessions are created, each with one LLM event
###
