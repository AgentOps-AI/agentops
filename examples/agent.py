from agentops import track_agent


@track_agent("name")
class test_agent:
    def __init__(self, property):
        self.property = property
        print("hello")


agent = test_agent("hi")
