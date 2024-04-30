import time

import agentops


agentops.init('b9ed7355-5b95-4f11-9ecf-3a65fdf4cd97')
@agentops.record_function('sleeping')
def sleep(num: int):
    print('sleeping')
    time.sleep(5)
    return num

sleep(2)
sleep(4)
agentops.end_session('Success')
