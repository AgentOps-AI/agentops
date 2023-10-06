import agentops
import asyncio
import openai


# from wandb.integration.openai import autolog
# autolog()


ao_client = agentops.Client(api_key='',
                            tags=['mock tests'])


openai.api_key = '3'


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
