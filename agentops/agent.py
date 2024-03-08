import uuid
from agentops import Client


def track_agent(name: str | None):
    def class_decorator(cls):
        cls._is_ao_agent = True
        cls._ao_agent_id = str(uuid.uuid4())
        cls._ao_agent_name = name or cls.__name__

        # create agent record
        ao_client = Client()
        ao_client.create_agent(cls._ao_agent_id, cls._ao_agent_name)
        return cls

    return class_decorator
