from agentops.sdk.decorators.agentops import session, agent, operation, record
import agentops


agentops.init()


@agent
class Agent:
    @operation
    def my_operation(self):
        print("Hello, world!")


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
