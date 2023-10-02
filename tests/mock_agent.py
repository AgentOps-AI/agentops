import agentops
import time

print('init')

ao_client = agentops.Client(api_key='floof',
                            tags=['mock tests'])


@ao_client.record_action('action')
def sleep_func(sleep):
    time.sleep(sleep)
    print('1')


@ao_client.record_action('multi')
def multi_event(sleep):
    sleep_func(1)
    time.sleep(sleep)


print('Action 1')
# ao_client.record_action('Action 1')
sleep_func(0.1)
print('Action 2 - 5 second sleep')
# ao_client.record_action('Action 2')
multi_event(3)
print('End Session')
ao_client.end_session(end_state='Fail')
