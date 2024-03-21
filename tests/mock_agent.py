import agentops
import time
import asyncio
from dotenv import load_dotenv

load_dotenv()


print('init')

agentops.init(tags=['mock tests'])

@agentops.record_function('action')
def sleep_func(sleep):
    time.sleep(sleep)
    print('sync sleep')
    try:
        raise ValueError
    except:
        ...


@agentops.record_function('async')
async def sleep_func_async(sleep):
    await asyncio.sleep(sleep)
    print('async sleep')
    try:
        raise ValueError
    except:
        ...


@agentops.record_function('multi')
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
    agentops.end_session(end_state='Success')


if __name__ == '__main__':
    asyncio.run(main())
    print('done')
