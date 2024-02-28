
import openai
import agentops
import asyncio
import os
import pkg_resources

print('Running OpenAI <v1.0.0')


ao_client = agentops.Client(
    tags=['mock tests', pkg_resources.get_distribution('openai').version]
)

openai.api_key = os.environ['OPENAI_API_KEY']


async def stream_achat():
    message = [{"role": "user", "content": "stream achat test"}]

    res = await openai.ChatCompletion.acreate(
        model='gpt-3.5-turbo', messages=message, temperature=0.5, stream=True)
    async for r in res:
        print(r)
    print('*'*100)


def stream_chat():
    message = [{"role": "user", "content": "stream chat test"}]
    res = openai.ChatCompletion.create(
        model='gpt-3.5-turbo', messages=message, temperature=0.5, stream=True)
    for r in res:
        print(r)
    print('*'*100)


async def achat():
    message = [{"role": "user", "content": "achat test"}]
    res = await openai.ChatCompletion.acreate(
        model='gpt-3.5-turbo', messages=message, temperature=0.5)
    print(res)

    print('*'*100)


def chat():
    message = [{"role": "user", "content": "chat test"}]
    res = openai.ChatCompletion.create(
        model='gpt-3.5-turbo', messages=message, temperature=0.5)
    print(res)

    print('*'*100)


print('running async stream')
asyncio.run(stream_achat())

print('running sync stream')
stream_chat()

print('running async chat')
asyncio.run(achat())

print('running sync chat')
chat()

ao_client.end_session('Success')
