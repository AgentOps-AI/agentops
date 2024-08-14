import agentops
from dotenv import load_dotenv
import litellm

load_dotenv()
agentops.init(default_tags=["litellm-provider-test"])

response = litellm.completion(
    model="gpt-3.5-turbo", messages=[{"content": "Hello, how are you?", "role": "user"}]
)

agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with one LLM event
###
