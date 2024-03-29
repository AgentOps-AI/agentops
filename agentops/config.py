"""
AgentOps configuration.

Classes:
    Configuration: Stores the configuration settings for AgentOps clients.
"""

from typing import Optional
from os import environ


class Configuration:
    """
    Stores the configuration settings for AgentOps clients.

    Args:
        api_key (str): API Key for AgentOps services
        endpoint (str, optional): The endpoint for the AgentOps service. Defaults to 'https://api.agentops.ai'.
        max_wait_time (int, optional): The maximum time to wait in milliseconds before flushing the queue. Defaults to 30000.
        max_queue_size (int, optional): The maximum size of the event queue. Defaults to 100.
    """

    def __init__(self, api_key: str,
                 parent_key: Optional[str],
                 endpoint: Optional[str] = environ.get('AGENTOPS_API_ENDPOINT', 'https://api.agentops.ai'),
                 max_wait_time: Optional[int] = None,
                 max_queue_size: Optional[int] = None):
        self._api_key: str = api_key
        self._endpoint = endpoint
        self._max_wait_time = max_wait_time or 30000
        self._max_queue_size = max_queue_size or 100
        self._parent_key: Optional[str] = parent_key

    @property
    def api_key(self) -> str:
        """
        Get the API Key for AgentOps services.

        Returns:
            str: The API Key for AgentOps services.
        """
        return self._api_key

    @api_key.setter
    def api_key(self, value: str):
        """
        Set the API Key for AgentOps services.

        Args:
            value (str): The new API Key.
        """
        self._api_key = value

    @property
    def endpoint(self) -> str:
        """
        Get the endpoint for the AgentOps service.

        Returns:
            str: The endpoint for the AgentOps service.
        """
        return self._endpoint

    @endpoint.setter
    def endpoint(self, value: str):
        """
        Set the endpoint for the AgentOps service.

        Args:
            value (str): The new endpoint.
        """
        self._endpoint = value

    @property
    def max_wait_time(self) -> int:
        """
        Get the maximum wait time for the AgentOps service.

        Returns:
            int: The maximum wait time.
        """
        return self._max_wait_time

    @max_wait_time.setter
    def max_wait_time(self, value: int):
        """
        Set the maximum wait time for the AgentOps service.

        Args:
            value (int): The new maximum wait time.
        """
        self._max_wait_time = value

    @property
    def max_queue_size(self) -> int:
        """
        Get the maximum size of the event queue.

        Returns:
            int: The maximum size of the event queue.
        """
        return self._max_queue_size

    @max_queue_size.setter
    def max_queue_size(self, value: int):
        """
        Set the maximum size of the event queue.

        Args:
            value (int): The new maximum size of the event queue.
        """
        self._max_queue_size = value

    @property
    def parent_key(self):
        return self._parent_key

    @parent_key.setter
    def parent_key(self, value: str):
        self._parent_key = value
