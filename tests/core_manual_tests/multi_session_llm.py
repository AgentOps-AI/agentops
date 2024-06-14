import agentops
from openai import OpenAI
from dotenv import load_dotenv
from agentops import ActionEvent

load_dotenv()
agentops.init(auto_start_session=False)
openai = OpenAI()

session_id_1 = agentops.start_session(tags=["multi-session-test-1"])
session_id_2 = agentops.start_session(tags=["multi-session-test-2"])

print("session_id_1: {}".format(session_id_1))
print("session_id_2: {}".format(session_id_2))

messages = [{"role": "user", "content": "Hello"}]

response = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=messages,
    temperature=0.5,
    session_id=session_id_1,  # <-- add the agentops session_id to the create function
)

agentops.record(ActionEvent(action_type="test event"), session_id=session_id_1)

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
