import uuid
from agentops import Client


def track_agent(name: str | None):
    def class_decorator(cls):
        cls._agent_ops_agent_name = name or cls.__name__

        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            self._agent_ops_agent_id = str(uuid.uuid4())
            ao_client = Client()
            ao_client.create_agent(self._agent_ops_agent_id, self._agent_ops_agent_name)
            original_init(self, *args, **kwargs)

        cls.__init__ = new_init
        return cls

    return class_decorator
