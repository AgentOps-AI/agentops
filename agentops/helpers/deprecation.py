"""
Deprecation utilities for AgentOps SDK.
"""

import functools
from typing import Set, Callable, Any
from agentops.logging import logger

# Track which deprecation warnings have been shown to avoid spam
_shown_warnings: Set[str] = set()


def deprecated(message: str):
    """
    Decorator to mark functions as deprecated.

    Args:
        message: Deprecation message to show
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warning_key = f"{func.__module__}.{func.__name__}"
            if warning_key not in _shown_warnings:
                logger.warning(f"{func.__name__}() is deprecated and will be removed in v4 in the future. {message}")
                _shown_warnings.add(warning_key)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def warn_deprecated_param(param_name: str, replacement: str = None):
    """
    Warn about deprecated parameter usage.

    Args:
        param_name: Name of the deprecated parameter
        replacement: Suggested replacement parameter
    """
    warning_key = f"param.{param_name}"
    if warning_key not in _shown_warnings:
        if replacement:
            message = f"Parameter '{param_name}' is deprecated and will be removed in v4 in the future. Use '{replacement}' instead."
        else:
            message = f"Parameter '{param_name}' is deprecated and will be removed in v4 in the future."
        logger.warning(message)
        _shown_warnings.add(warning_key)
