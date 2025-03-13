"""Environment variable helper functions"""

import os
from typing import List, Optional, Set


def get_env_bool(key: str, default: bool) -> bool:
    """Get boolean from environment variable

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        bool: Parsed boolean value
    """
    val = os.getenv(key)
    if val is None:
        return default
    return val.lower() in ("true", "1", "t", "yes")


def get_env_int(key: str, default: int) -> int:
    """Get integer from environment variable

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        int: Parsed integer value
    """
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def get_env_list(key: str, default: Optional[List[str]] = None) -> Set[str]:
    """Get comma-separated list from environment variable

    Args:
        key: Environment variable name
        default: Default list if not set

    Returns:
        Set[str]: Set of parsed values
    """
    val = os.getenv(key)
    if val is None:
        return set(default or [])
    return set(val.split(","))
