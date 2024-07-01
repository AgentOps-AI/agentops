from enum import Enum


class EventType(Enum):
    LLM = "llms"
    ACTION = "actions"
    API = "apis"
    TOOL = "tools"
    ERROR = "errors"


class EndState(Enum):
    SUCCESS = "Success"
    FAIL = "Fail"
    INDETERMINATE = "Indeterminate"
