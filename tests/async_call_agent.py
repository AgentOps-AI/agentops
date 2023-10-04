import asyncio
import openai
from openai import ChatCompletion

import agentops

ao_client = agentops.Client(api_key='',
                            tags=['mock tests'])
openai.api_key = ''

message = [{"role": "user", "content": "Hello"},
           {"role": "assistant", "content": "Hi there!"}]


async def chat():
    await ChatCompletion.acreate(
        model='gpt-3.5-turbo', messages=message, temperature=0.5)

print('running async call')
asyncio.run(chat())
print('running async call')
ao_client.end_session('Success')
