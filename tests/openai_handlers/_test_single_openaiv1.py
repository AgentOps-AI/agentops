from openai import OpenAI, AsyncOpenAI
import openai
import agentops
from dotenv import load_dotenv
load_dotenv()
client = OpenAI()

async_client = AsyncOpenAI()

# Assuming that initializing will trigger the LlmTracker to override methods
agentops.init(tags=['mock agent', openai.__version__])

# Now the client.chat.completions.create should be the overridden method
print('Chat completion')
chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Say this is a test",
        }
    ],
    model="gpt-3.5-turbo",
)

agentops.end_session('Success')
