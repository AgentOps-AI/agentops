from enum import Enum


class EventType(Enum):
    LLM = "llms"
    ACTION = "actions"
    API = "apis"
    TOOL = "tools"
    ERROR = "errors"


class EndState(Enum):
    """
    Enum representing the possible end states of a session.

    Attributes:
        SUCCESS: Indicates the session ended successfully.
        FAIL: Indicates the session failed.
        INDETERMINATE (default): Indicates the session ended with an indeterminate state.
                       This is the default state if not specified, e.g. if you forget to call end_session()
                       at the end of your program or don't pass it the end_state parameter
    """

    SUCCESS = "Success"
    FAIL = "Fail"
    INDETERMINATE = "Indeterminate"  # Default
