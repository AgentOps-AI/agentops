"""
AgentOps configuration.

Classes:
    Configuration: Stores the configuration settings for AgentOps clients.
"""

from typing import Optional
from os import environ
from .log_config import logger


class Configuration:
    """
    Stores the configuration settings for AgentOps clients.

    Args:
        api_key (str, optional): API Key for AgentOps services. If none is provided, key will
            be read from the AGENTOPS_API_KEY environment variable.
        parent_key (str, optional): Organization key to give visibility of all user sessions the user's organization. If none is provided, key will
            be read from the AGENTOPS_PARENT_KEY environment variable.
        endpoint (str, optional): The endpoint for the AgentOps service. If none is provided, key will
            be read from the AGENTOPS_API_ENDPOINT environment variable. Defaults to 'https://api.agentops.ai'.
        max_wait_time (int, optional): The maximum time to wait in milliseconds before flushing the queue. Defaults to 5000.
        max_queue_size (int, optional): The maximum size of the event queue. Defaults to 100.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        parent_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        max_wait_time: Optional[int] = None,
        max_queue_size: Optional[int] = None,
        skip_auto_end_session: Optional[bool] = False,
    ):

        if not api_key:
            api_key = environ.get("AGENTOPS_API_KEY", None)
            if not api_key:
                raise ConfigurationError(
                    "No API key provided - no data will be recorded."
                )

        if not parent_key:
            parent_key = environ.get("AGENTOPS_PARENT_KEY", None)

        if not endpoint:
            endpoint = environ.get("AGENTOPS_API_ENDPOINT", "https://api.agentops.ai")

        self._api_key: str = api_key
        self._endpoint = endpoint
        self._max_wait_time = max_wait_time or 5000
        self._max_queue_size = max_queue_size or 100
        self._parent_key: Optional[str] = parent_key
        self._skip_auto_end_session: Optional[bool] = skip_auto_end_session

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
        return self._endpoint  # type: ignore

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

    @property
    def skip_auto_end_session(self):
        return self._skip_auto_end_session

    @parent_key.setter
    def parent_key(self, value: str):
        self._parent_key = value


class ConfigurationError(Exception):
    """Exception raised for errors related to Configuration"""

    def __init__(self, message: str):
        super().__init__(message)
        logger.warning(message)
