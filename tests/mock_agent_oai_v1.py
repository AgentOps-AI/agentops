# from openai import OpenAI
from openai import OpenAI
import agentops
from dotenv import load_dotenv

load_dotenv()


print('Running OpenAI v1.0.0+')

# ao_client = agentops.Client(tags=['mock tests'])
client = OpenAI()
ao_client = agentops.Client(
    tags=['mock agent'])


chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Say this is a test",
        }
    ],
    model="gpt-3.5-turbo",
)

print(chat_completion.choices)
ao_client.end_session('Success')
