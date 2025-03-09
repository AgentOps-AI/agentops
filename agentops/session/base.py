from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from agentops.config import Config, default_config
from agentops.helpers import get_host_env


class SessionBase(ABC):
    """Base class for Session"""

    auto_start: bool
    host_env: dict
    config: Config
    tags: List[str]

    def __init__(self, *args, **kwargs):
        # Set default values in kwargs
        kwargs.setdefault("host_env", get_host_env())
        kwargs.setdefault("config", default_config())
        kwargs.setdefault("auto_start", True)
        kwargs.setdefault("tags", [])
        
        # Assign instance attributes from kwargs
        self.host_env = kwargs["host_env"]
        self.config = kwargs["config"]
        self.auto_start = kwargs["auto_start"]
        self.tags = kwargs["tags"]

    @property
    def session_url(self) -> str:
        """URL to view this trace in the dashboard"""
        return f"{self.config.endpoint}/drilldown?session_id={self.session_id}"

    # --------------------------------------------------------------------------

    def start(self):
        raise NotImplementedError

    def end(self):
        raise NotImplementedError

    @property
    def session_id(self) -> UUID:
        raise NotImplementedError

    def dict(self) -> dict:
        raise NotImplementedError

    def json(self) -> str:
        raise NotImplementedError
