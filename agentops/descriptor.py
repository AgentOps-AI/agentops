import inspect
import logging
from typing import Union
from uuid import UUID


class agentops_property:
    """
    A descriptor that provides a standardized way to handle agent property access and storage.
    Properties are automatically stored with an '_agentops_' prefix to avoid naming conflicts.

    The descriptor can be used in two ways:
    1. As a class attribute directly
    2. Added dynamically through a decorator (like @track_agent)

    Attributes:
        private_name (str): The internal name used for storing the property value,
            prefixed with '_agentops_'. Set either through __init__ or __set_name__.

    Example:
        ```python
        # Direct usage in a class
        class Agent:
            name = agentops_property()
            id = agentops_property()

            def __init__(self):
                self.name = "Agent1"  # Stored as '_agentops_name'
                self.id = "123"       # Stored as '_agentops_id'

        # Usage with decorator
        @track_agent()
        class Agent:
            pass
            # agentops_agent_id and agentops_agent_name are added automatically
        ```

    Notes:
        - Property names with 'agentops_' prefix are automatically stripped when creating
          the internal storage name
        - Returns None if the property hasn't been set
        - The descriptor will attempt to resolve property names even when added dynamically
    """

    def __init__(self, name=None):
        """
        Initialize the descriptor.

        Args:
            name (str, optional): The name for the property. Used as fallback when
                the descriptor is added dynamically and __set_name__ isn't called.
        """
        self.private_name = None
        if name:
            self.private_name = f"_agentops_{name.replace('agentops_', '')}"

    def __set_name__(self, owner, name):
        """
        Called by Python when the descriptor is defined directly in a class.
        Sets up the private name used for attribute storage.

        Args:
            owner: The class that owns this descriptor
            name: The name given to this descriptor in the class
        """
        self.private_name = f"_agentops_{name.replace('agentops_', '')}"

    def __get__(self, obj, objtype=None):
        """
        Get the property value.

        Args:
            obj: The instance to get the property from
            objtype: The class of the instance

        Returns:
            The property value, or None if not set
            The descriptor itself if accessed on the class rather than an instance

        Raises:
            AttributeError: If the property name cannot be determined
        """
        if obj is None:
            return self

        # Handle case where private_name wasn't set by __set_name__
        if self.private_name is None:
            # Try to find the name by looking through the class dict
            for name, value in type(obj).__dict__.items():
                if value is self:
                    self.private_name = f"_agentops_{name.replace('agentops_', '')}"
                    break
            if self.private_name is None:
                raise AttributeError("Property name could not be determined")

        # First try getting from object's __dict__ (for Pydantic)
        if hasattr(obj, "__dict__"):
            dict_value = obj.__dict__.get(self.private_name[1:])
            if dict_value is not None:
                return dict_value

        # Fall back to our private storage
        return getattr(obj, self.private_name, None)

    def __set__(self, obj, value):
        """
        Set the property value.

        Args:
            obj: The instance to set the property on
            value: The value to set

        Raises:
            AttributeError: If the property name cannot be determined
        """
        if self.private_name is None:
            # Same name resolution as in __get__
            for name, val in type(obj).__dict__.items():
                if val is self:
                    self.private_name = f"_agentops_{name.replace('agentops_', '')}"
                    break
            if self.private_name is None:
                raise AttributeError("Property name could not be determined")

        # Set in both object's __dict__ (for Pydantic) and our private storage
        if hasattr(obj, "__dict__"):
            obj.__dict__[self.private_name[1:]] = value
        setattr(obj, self.private_name, value)

    def __delete__(self, obj):
        """
        Delete the property value.

        Args:
            obj: The instance to delete the property from

        Raises:
            AttributeError: If the property name cannot be determined
        """
        if self.private_name is None:
            raise AttributeError("Property name could not be determined")
        try:
            delattr(obj, self.private_name)
        except AttributeError:
            pass

    @staticmethod
    def stack_lookup() -> Union[UUID, None]:
        """
        Look through the call stack to find an agent ID.

        This method searches the call stack for objects that have agentops_property
        descriptors and returns the agent_id if found.

        Returns:
            UUID: The agent ID if found in the call stack
            None: If no agent ID is found or if "__main__" is encountered
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
                    class_attrs = {name: getattr(var_type, name, None) for name in dir(var_type)}

                    agent_id_desc = class_attrs.get("agentops_agent_id")

                    if isinstance(agent_id_desc, agentops_property):
                        agent_id = agent_id_desc.__get__(var, var_type)

                        if agent_id:
                            agent_name_desc = class_attrs.get("agentops_agent_name")
                            if isinstance(agent_name_desc, agentops_property):
                                agent_name = agent_name_desc.__get__(var, var_type)
                                return agent_id
                except Exception:
                    continue

        return None
