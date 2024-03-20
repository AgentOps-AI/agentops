from agentops import Client
from agentops.event import Event


def record(event: Event):
    ao_client = Client()
    ao_client.record(event)

