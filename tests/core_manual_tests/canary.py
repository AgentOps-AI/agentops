import agentops
from openai import OpenAI
from dotenv import load_dotenv
from agentops import ActionEvent

load_dotenv()
agentops.init(default_tags=["canary"])
openai = OpenAI()

messages = [{"role": "user", "content": "Hello"}]

# option 1: use session.patch
response = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=messages,
    temperature=0.5,
)

agentops.record(ActionEvent(action_type="test event"))

agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with one LLM event
###
