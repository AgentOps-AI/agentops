import time

import agentops


agentops.init('b9ed7355-5b95-4f11-9ecf-3a65fdf4cd97')
@agentops.record_function('sleep')
def sleep():
    print('sleeping')
    time.sleep(3)


sleep()
agentops.end_session('Success')


