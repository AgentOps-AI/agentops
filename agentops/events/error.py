from ..event import Event, EventType
from typing import Optional


class ErrorEvent(Event):
    def __init__(self, error_type: Optional[str] = None, code: Optional[str] = None, details: Optional[str] = None, logs: Optional[str] = None, **kwargs):
        super().__init__(event_type=EventType.error, **kwargs)
        self.error_type = error_type  # TODO: type is a reserved word
        self.code = code,
        self.details = details,
        self.logs = logs,

    def __str__(self):
        super_str = super().__str__()
        self_str = {
            "error_type": self.error_type,
            "code": self.code,
            "details": self.details,
            "logs": self.logs
        }
        return str({**super_str, **self_str})
