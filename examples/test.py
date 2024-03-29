import agentops


AGENTOPS_API_KEY = "6b7a1469-bdcb-4d47-85ba-c4824bc8486e"
agentops.init(AGENTOPS_API_KEY, endpoint="http://localhost:8000")

from agentops import record_function

@record_function("add numbers")
def add(x, y):
    return x + y

add(2,4)