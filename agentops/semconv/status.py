"""Status enumerations for spans."""

from enum import Enum


class ToolStatus(Enum):
    """Tool status values."""

    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
