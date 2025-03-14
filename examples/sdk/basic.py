import agentops
from agentops.sdk.decorators import agent, operation, session

agentops.init()


@agent
class Agent:

    @operation
    def nested_operation(self):
        print("Hello, world!")

    @operation
    def my_operation(self):
        print("Hello, world!")
        self.nested_operation()


@session
def session_one():
    agent = Agent()
    agent.my_operation()


@session
def session_two():
    agent = Agent()
    agent.my_operation()


session_one()
session_two()
