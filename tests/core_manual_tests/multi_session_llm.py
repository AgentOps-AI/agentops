import agentops
from openai import OpenAI
from dotenv import load_dotenv
from agentops import ActionEvent

load_dotenv()
agentops.init(auto_start_session=False, endpoint="http://localhost:8000")
openai = OpenAI()

session_1 = agentops.start_session(tags=["multi-session-test-1"])
session_2 = agentops.start_session(tags=["multi-session-test-2"])

print("session_id_1: {}".format(session_1))
print("session_id_2: {}".format(session_2))

messages = [{"role": "user", "content": "Hello"}]

response = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=messages,
    temperature=0.5,
    session=session_1,  # <-- add the agentops session_id to the create function
)

session_1.record(ActionEvent(action_type="test event"))

response = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=messages,
    temperature=0.5,
    session=session_2,  # <-- add the agentops session_id to the create function
)

session_1.end_session(end_state="Success")
session_2.end_session(end_state="Success")

###
#  Used to verify that two sessions are created, each with one LLM event
###
