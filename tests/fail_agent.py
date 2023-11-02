import agentops
import time
import asyncio
from dotenv import load_dotenv

load_dotenv()


print('init')

ao_client = agentops.Client(tags=['mock tests'])


@ao_client.record_action('fail')
def fail_func(sleep):
    time.sleep(sleep)
    print('sync sleep')

    print(1/0)


@ao_client.record_action('sleep')
def sleep_func(sleep):
    time.sleep(sleep)
    print('sync sleep')


async def main():

    print('Action 1')
    sleep_func(0.1)
    fail_func(0.1)

    ao_client.end_session(end_state='Success')


if __name__ == '__main__':
    asyncio.run(main())
    print('done')
