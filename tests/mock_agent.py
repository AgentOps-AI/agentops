import agentops
import time
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()


print('init')

ao_client = agentops.Client(tags=['mock tests'])


@ao_client.record_action('action')
def sleep_func(sleep):
    time.sleep(sleep)
    print('sync sleep')
    try:
        raise ValueError
    except:
        ...


@ao_client.record_action('async')
async def sleep_func_async(sleep):
    await asyncio.sleep(sleep)
    print('async sleep')
    try:
        raise ValueError
    except:
        ...


@ao_client.record_action('multi')
def multi_event(sleep):
    sleep_func(1)
    time.sleep(sleep)


async def main():

    print('Action 1')
    try:
        sleep_func(0.1)
    except:
        pass

    try:
        multi_event(3)
    except:
        pass

    task1 = asyncio.create_task(sleep_func_async(3))
    task2 = asyncio.create_task(sleep_func_async(3))
    await task1
    await task2

    print('Action 1')
    try:
        sleep_func(0.1)
    except:
        pass
    print('End Session')
    ao_client.end_session(end_state='Success')


if __name__ == '__main__':
    asyncio.run(main())
    print('done')
