import agentops
from openai import OpenAI
from dotenv import load_dotenv
from agentops import ActionEvent

load_dotenv()
agentops.init(auto_start_session=False)
openai = OpenAI()

session_1 = agentops.start_session(tags=["multi-session-test-1"])
session_2 = agentops.start_session(tags=["multi-session-test-2"])

print("session_id_1: {}".format(session_1.session_id))
print("session_id_2: {}".format(session_2.session_id))

messages = [{"role": "user", "content": "Hello"}]

# option 1: use session.patch
response = session_1.patch(openai.chat.completions.create)(
    model="gpt-3.5-turbo",
    messages=messages,
    temperature=0.5,
)

session_1.record(ActionEvent(action_type="test event"))

# option 2: add session as a keyword argument
response2 = openai.chat.completions.create(
    model="gpt-3.5-turbo", messages=messages, temperature=0.5, session=session_2
)

session_1.end_session(end_state="Success")
session_2.end_session(end_state="Success")

###
#  Used to verify that two sessions are created, each with one LLM event
###
