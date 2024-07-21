from typing import Union

from .log_config import logger
from uuid import uuid4
from agentops import Client
from inspect import isclass, isfunction
from .state import (
    is_initialized,
)  # sketch, Python's own docs say not to do this but this is the only way Python will accept it

# https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules
# Stackoverflow (this might not be applicable bc you can't un-init): Don't use a from import unless the variable is intended to be a constant. from shared_stuff import a would create a new a variable initialized to whatever shared_stuff.a referred to at the time of the import, and this new a variable would not be affected by assignments to shared_stuff.a.
# https://stackoverflow.com/questions/15959534/visibility-of-global-variables-in-imported-modules


def track_agent(name: Union[str, None] = None):
    def decorator(obj):
        if name:
            obj.agent_ops_agent_name = name

        if isclass(obj):
            original_init = obj.__init__

            def new_init(self, *args, **kwargs):
                try:
                    original_init(self, *args, **kwargs)

                    if not is_initialized:
                        return

                    self.agent_ops_agent_id = str(uuid4())

                    session = kwargs.get("session", None)
                    if session is not None:
                        self.agent_ops_session_id = session.session_id

                    Client().create_agent(
                        name=self.agent_ops_agent_name,
                        agent_id=self.agent_ops_agent_id,
                        session=session,
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
