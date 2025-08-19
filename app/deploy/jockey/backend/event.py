from __future__ import annotations
from typing import Optional, Any, ClassVar, TypedDict, Type
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, UTC


_registry: dict[str, Type['BaseEvent']] = {}


class SerializedEvent(TypedDict):
    """Type definition for serialized event data."""

    event_type: str
    status: str
    timestamp: str
    message: str
    payload: dict[str, Any]  # The original payload dict from the event
    kwargs: dict[str, Any]  # Class attributes that were set on the event instance


class EventStatus(Enum):
    STARTED = "started"
    PROGRESS = "progress"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"


class BaseEvent(ABC):
    """Abstract base event class for all operations.

    Provides consistent status and message handling across all operation types.
    Subclasses must define an 'event_type' class variable and can add operation-specific fields.

    The message field is used for all communication - both success and error states.
    When status is ERROR, the message contains the error description.

    The payload field can contain structured data relevant to the operation.
    The exception field can contain an exception instance for error events.
    The event_type class variable identifies the specific event type for easy string matching.
    """

    event_type: ClassVar[str]  # Must be defined in subclasses

    status: EventStatus
    timestamp: datetime
    payload: dict[str, Any]
    exception: Optional[Exception]
    _message: Optional[str]  # Pre-computed message

    def __init__(self, status: EventStatus, /, **kwargs) -> None:
        """Initialize with status as positional argument and any additional fields.

        Args:
            status: The event status (positional-only)
            **kwargs: Additional fields to set as attributes including optional 'message'
        """
        self.status = status

        if 'timestamp' in kwargs:
            self.timestamp = datetime.fromisoformat(kwargs.pop('timestamp')).astimezone(UTC)
        else:
            self.timestamp = datetime.now(UTC)

        self.payload = kwargs.pop('payload', {})
        self.exception = kwargs.pop('exception', None)
        self._message = kwargs.pop('message', None)  # Store pre-computed message if provided

        # Set any additional fields from kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    @abstractmethod
    def format_message(self) -> str:
        """Generate a human-readable message based on the event's status and attributes.

        This method must be implemented by all subclasses to provide context-specific
        messages that are generated dynamically from the event's state.
        """
        pass

    @property
    def message(self) -> str:
        """Get the event message, using stored message if available, otherwise format dynamically."""
        if self._message is not None:
            return self._message
        return self.format_message()

    def serialize(self) -> SerializedEvent:
        """Serialize the event to a dictionary for storage or transmission.

        Returns:
            SerializedEvent
        """
        kwargs = {}
        for key, value in self.__dict__.items():
            if key not in ["status", "payload", "exception", "_message"] and not key.startswith('_'):
                if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                    kwargs[key] = value  # type: ignore
                elif hasattr(value, 'value'):  # Handle enums
                    kwargs[key] = value.value  # type: ignore
                else:
                    kwargs[key] = str(value)

        return SerializedEvent(
            event_type=self.event_type,
            status=self.status.value,
            timestamp=self.timestamp.isoformat(),
            message=self.message,
            payload=self.payload,
            kwargs=kwargs,
        )


def register_event(event_class: Type['BaseEvent']) -> None:
    """Register an event class in the global event registry.

    Args:
        event_class: The event class to register
    """
    global _registry

    _registry[event_class.event_type] = event_class


def deserialize_event(serialized: SerializedEvent) -> Optional[BaseEvent]:
    """Deserialize a serialized event back to a BaseEvent object.

    Args:
        serialized: The serialized event data

    Returns:
        BaseEvent instance of the appropriate type, or None if unknown event type
    """
    global _registry

    event_type = serialized["event_type"]
    event_class = _registry.get(event_type)

    if not event_class:
        # TODO we could be nicer
        raise ValueError(f"Unknown event type: {event_type}")

    # The `kwargs` contain the class attributes from event subclasses
    # The `payload` contains the original payload dict
    # Pass the pre-computed `message` to preserve exact error details
    # TODO we do not re-instantiate the `exception` here and rely on the precomputed message
    return event_class(
        EventStatus(serialized["status"]),
        message=serialized["message"],
        payload=serialized["payload"],
        **serialized["kwargs"],
    )
