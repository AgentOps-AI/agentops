import agentops
import time

print('init')

ao_client = agentops.Client(api_key='floof', tags=['mock tests'])


print('Action 1')
ao_client.record_action('Action 1')
time.sleep(0.1)
print('Action 2')
ao_client.record_action('Action 2')
time.sleep(10)
print('End Session')
ao_client.end_session(end_state='Fail')
