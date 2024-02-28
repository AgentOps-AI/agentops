"""
AgentOps events.

Classes:
    Event: Represents discrete events to be recorded.
"""
from abc import ABC, abstractmethod
from .helpers import get_ISO_time
from typing import Optional, List
from enum import EventType


class Event(ABC):
    """
    Represents a discrete event to be recorded.
    """

    def __init__(self, event_type: EventType = EventType.action,
                 tags: Optional[List[str]] = None,
                 init_timestamp: Optional[str] = None,
                 ):
        self.event_type = event_type
        self.tags = tags
        self.end_timestamp = get_ISO_time()
        self.init_timestamp = init_timestamp if init_timestamp else self.end_timestamp

    @abstractmethod
    def __str__(self):
        return str({
            "event_type": self.event_type,
            "tags": self.tags,
            "init_timestamp": self.init_timestamp,
        })
