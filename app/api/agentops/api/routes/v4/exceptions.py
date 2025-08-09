"""Custom Exceptions for the v4 endpoints"""

from typing import Optional


class InvalidParameterError(Exception):
    """Exception raised for invalid parameter values."""

    def __init__(self, param_name: str, message: str):
        self.param_name = param_name
        self.message = message
        super().__init__(f"Invalid parameter '{param_name}': {message}")


class DatabaseError(Exception):
    """Exception raised for database-related errors."""

    def __init__(self, message: str, query: Optional[str] = None):
        self.message = message
        self.query = query
        super().__init__(f"Database error: {message}")
