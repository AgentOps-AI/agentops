import openai
from openai import ChatCompletion

import agentops

ao_client = agentops.Client(api_key='',
                            endpoint="http://localhost:8000",
                            tags=['mock tests'])

openai.api_key = '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'

message = [{"role": "user", "content": "Hello"},
           {"role": "assistant", "content": "Hi there!"}]

ChatCompletion.create(
    model='gpt-3.5-turbo', messages=message, temperature=0.5)

ao_client.end_session('Success')
