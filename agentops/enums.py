from enum import Enum, auto

class Result(Enum):
    SUCCESS = "Success"
    FAIL = "Fail"
    INDETERMINATE = "Indeterminate"

class ActionType(Enum):
    ACTION = "action"
    API = "api"
    LLM = "llm"
    SCREENSHOT = "screenshot"
    TOOL = "tool"
    ERROR = "error"
