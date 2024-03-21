from uuid import uuid4
from agentops import Client
from inspect import isclass, isfunction


def track_agent(name: str | None = None):
    def decorator(obj):
        if name:
            obj.agent_ops_agent_name = name

        if isclass(obj):
            original_init = obj.__init__

            def new_init(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                self.agent_ops_agent_id = uuid4()
                ao_client = Client()
                ao_client.create_agent(self.agent_ops_agent_id, self.agent_ops_agent_name)

            obj.__init__ = new_init

        elif isfunction(obj):
            obj.agent_ops_agent_id = uuid4()
            ao_client = Client()
            ao_client.create_agent(obj.agent_ops_agent_id, obj.agent_ops_agent_name)

        else:
            raise Exception("Invalid input, 'obj' must be a class or a function")

        return obj

    return decorator
