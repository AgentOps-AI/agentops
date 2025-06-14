"""Common version utilities for instrumentations."""

from typing import Optional
from agentops.logging import logger


def get_package_version(package_name: str, display_name: Optional[str] = None) -> str:
    """Get the version of a package, or 'unknown' if not found.

    Args:
        package_name: The name of the package as used in pip/importlib (e.g., 'openai', 'anthropic', 'mem0ai')
        display_name: Optional display name for logging messages (defaults to package_name)

    Returns:
        The version string of the package or 'unknown'
    """
    try:
        from importlib.metadata import version

        return version(package_name)
    except ImportError:
        display = display_name or package_name
        logger.debug(f"Could not find {display} SDK version")
        return "unknown"
