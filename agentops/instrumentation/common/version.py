"""Version utilities for AgentOps instrumentation.

This module provides common functionality for retrieving and managing
library versions across all instrumentation modules.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_library_version(package_name: str, default_version: str = "unknown") -> str:
    """Get the version of a library package.

    Attempts to retrieve the installed version of a package using importlib.metadata.
    Falls back to the default version if the version cannot be determined.

    Args:
        package_name: The name of the package to get the version for (as used in pip/importlib.metadata)
        default_version: The default version to return if the package version cannot be found

    Returns:
        The version string of the package or the default version

    Examples:
        >>> get_library_version("openai")
        "1.0.0"

        >>> get_library_version("nonexistent-package")
        "unknown"

        >>> get_library_version("ibm-watsonx-ai", "1.3.11")
        "1.3.11"  # If not found
    """
    try:
        from importlib.metadata import version

        return version(package_name)
    except (ImportError, Exception) as e:
        logger.debug(f"Could not find {package_name} version: {e}")
        return default_version


class LibraryInfo:
    """Container for library information used in instrumentation.

    This class provides a standardized way to store and access library
    information (name and version) across all instrumentors.

    Attributes:
        name: The library name used for identification
        version: The library version string
        package_name: The package name used in pip/importlib.metadata (optional)
    """

    def __init__(self, name: str, package_name: Optional[str] = None, default_version: str = "unknown"):
        """Initialize library information.

        Args:
            name: The library name used for identification
            package_name: The package name used in pip/importlib.metadata.
                         If not provided, uses the library name.
            default_version: Default version if package version cannot be determined
        """
        self.name = name
        self.package_name = package_name or name
        self.version = get_library_version(self.package_name, default_version)

    def __repr__(self) -> str:
        return f"LibraryInfo(name={self.name!r}, version={self.version!r})"
