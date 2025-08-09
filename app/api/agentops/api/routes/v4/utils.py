from typing import Optional, TypeVar, ParamSpec
from collections import OrderedDict

from fastapi.responses import JSONResponse

from agentops.api.routes.v4.exceptions import InvalidParameterError

P = ParamSpec("P")
R = TypeVar("R")


def create_error_response(error_type: str, status_code: int, message: str, **extra_fields) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        error_type: Type of the error (e.g., "Invalid parameter", "Database error")
        status_code: HTTP status code
        message: Error message
        **extra_fields: Additional fields to include in the response

    Returns:
        JSONResponse with standardized format
    """
    # Use OrderedDict to ensure field order matches test expectations
    content = OrderedDict()
    content["error"] = error_type

    # For InvalidParameterError, order should be error, param, message
    if "param" in extra_fields:
        content["param"] = extra_fields.pop("param")

    content["message"] = message

    # Add any remaining extra fields
    for key, value in extra_fields.items():
        content[key] = value

    return JSONResponse(status_code=status_code, content=content)


def validate_status_code(status_code: Optional[str]) -> Optional[str]:
    """Validate status code parameter."""
    if not status_code:
        return None

    valid_status_codes = ["OK", "ERROR", "UNSET"]
    if status_code not in valid_status_codes:
        raise InvalidParameterError(
            "status_code", f"Invalid status code. Expected one of: {', '.join(valid_status_codes)}."
        )

    return status_code
