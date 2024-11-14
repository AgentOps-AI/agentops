import inspect
from typing import Any, Optional, Union
from uuid import UUID


class AgentOpsDescriptor:
    """Property Descriptor for handling agent-related properties"""

    def __init__(self, name: str):
        self.name = f"_agentops_{name}"

    def __get__(self, obj: Any, objtype=None) -> Optional[Any]:
        return getattr(obj, self.name, None)

    def __set__(self, obj: Any, value: Any):
        setattr(obj, self.name, value)

    @staticmethod
    def from_stack() -> Union[UUID, None]:
        """
        Look through the call stack for the class that called the LLM.
        Checks specifically for AgentOpsDescriptor descriptors.
        """
        for frame_info in inspect.stack():
            local_vars = frame_info.frame.f_locals

            for var_name, var in local_vars.items():
                # Stop at main
                if var == "__main__":
                    return None

                try:
                    # Check if object has our AgentOpsDescriptor descriptors
                    var_type = type(var)

                    # Get all class attributes
                    class_attrs = {
                        name: getattr(var_type, name, None) for name in dir(var_type)
                    }

                    agent_id_desc = class_attrs.get("agent_ops_agent_id")

                    if isinstance(agent_id_desc, AgentOpsDescriptor):
                        agent_id = agent_id_desc.__get__(var, var_type)

                        if agent_id:
                            agent_name_desc = class_attrs.get("agent_ops_agent_name")
                            if isinstance(agent_name_desc, AgentOpsDescriptor):
                                agent_name = agent_name_desc.__get__(var, var_type)
                                return agent_id
                    # elif
                except Exception as e:
                    continue

        return None
