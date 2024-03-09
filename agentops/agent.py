import uuid
from agentops import Client
from inspect import isclass, isfunction


def track_agent(name: str | None):
    def decorator(obj):
        obj._agent_ops_agent_name = name or obj.__name__

        if isclass(obj):
            original_init = obj.__init__

            def new_init(self, *args, **kwargs):
                self._agent_ops_agent_id = str(uuid.uuid4())
                ao_client = Client()
                ao_client.create_agent(self._agent_ops_agent_id, self._agent_ops_agent_name)
                original_init(self, *args, **kwargs)

            obj.__init__ = new_init

        elif isfunction(obj):
            obj._agent_ops_agent_id = str(uuid.uuid4())
            ao_client = Client()
            ao_client.create_agent(obj._agent_ops_agent_id, obj._agent_ops_agent_name)

        else:
            raise Exception("Invalid input, 'obj' must be a class or a function")

        return obj

    return decorator
