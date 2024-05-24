from typing import Union

from .log_config import logger
from uuid import uuid4
from agentops import Client
from inspect import isclass, isfunction


def track_agent(name: Union[str, None] = None):
    def decorator(obj):
        if name:
            obj.agent_ops_agent_name = name

        if isclass(obj):
            original_init = obj.__init__

            def new_init(self, *args, **kwargs):
                try:
                    original_init(self, *args, **kwargs)
                    self.agent_ops_agent_id = str(uuid4())
                    Client().create_agent(
                        name=self.agent_ops_agent_name, agent_id=self.agent_ops_agent_id
                    )
                except AttributeError as e:
                    logger.warning(
                        "Failed to track an agent. This often happens if agentops.init() was not "
                        "called before initializing an agent with the @track_agent decorator."
                    )
                    raise e

            obj.__init__ = new_init

        elif isfunction(obj):
            obj.agent_ops_agent_id = str(uuid4())
            Client().create_agent(
                name=obj.agent_ops_agent_name, agent_id=obj.agent_ops_agent_id
            )

        else:
            raise Exception("Invalid input, 'obj' must be a class or a function")

        return obj

    return decorator
