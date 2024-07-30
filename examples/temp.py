import agentops
from agentops import ActionEvent
from agent import agent

print("init")
agentops.init(tags=["test"], endpoint="http://localhost:8000")

agentops.record(ActionEvent("Test Event"))

agentops.end_session("Success")
