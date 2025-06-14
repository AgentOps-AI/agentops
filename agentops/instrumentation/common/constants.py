"""Common constants and initialization utilities for instrumentations."""

from typing import Tuple, Optional
import logging
from agentops.instrumentation.common.version import get_package_version


class InstrumentationConstants:
    """Base class for instrumentation constants and initialization."""

    def __init__(
        self,
        library_name: str,
        library_version: str,
        package_name: str,
        display_name: Optional[str] = None,
        module_path: Optional[str] = None,
    ):
        """Initialize instrumentation constants.

        Args:
            library_name: The library name used in telemetry (e.g., "agentops.instrumentation.openai")
            library_version: The instrumentation version (e.g., "1.0.0")
            package_name: The pip package name for version detection (e.g., "openai", "mem0ai")
            display_name: Optional display name for logging (defaults to package_name)
            module_path: Optional module path for the instrumentor class (for __all__ exports)
        """
        self.LIBRARY_NAME = library_name
        self.LIBRARY_VERSION = library_version
        self.PACKAGE_VERSION = get_package_version(package_name, display_name)
        self.logger = logging.getLogger(library_name)
        self._module_path = module_path

    def get_exports(self, instrumentor_class_name: str) -> list[str]:
        """Get the standard __all__ exports list.

        Args:
            instrumentor_class_name: Name of the instrumentor class

        Returns:
            List of exported names
        """
        exports = [
            "LIBRARY_NAME",
            "LIBRARY_VERSION",
            "PACKAGE_VERSION",
            instrumentor_class_name,
        ]
        return exports

    def get_constants(self) -> dict[str, str]:
        """Get a dictionary of all constants.

        Returns:
            Dictionary with LIBRARY_NAME, LIBRARY_VERSION, and PACKAGE_VERSION
        """
        return {
            "LIBRARY_NAME": self.LIBRARY_NAME,
            "LIBRARY_VERSION": self.LIBRARY_VERSION,
            "PACKAGE_VERSION": self.PACKAGE_VERSION,
        }


def setup_instrumentation_module(
    library_name: str,
    library_version: str,
    package_name: str,
    display_name: Optional[str] = None,
) -> Tuple[str, str, str, logging.Logger]:
    """Setup common instrumentation module components.

    This function standardizes the initialization of instrumentation modules by:
    - Getting the package version
    - Setting up logging
    - Returning standard constants

    Args:
        library_name: The library name used in telemetry
        library_version: The instrumentation version
        package_name: The pip package name for version detection
        display_name: Optional display name for logging

    Returns:
        Tuple of (LIBRARY_NAME, LIBRARY_VERSION, PACKAGE_VERSION, logger)
    """
    LIBRARY_NAME = library_name
    LIBRARY_VERSION = library_version
    PACKAGE_VERSION = get_package_version(package_name, display_name)
    logger = logging.getLogger(library_name)

    return LIBRARY_NAME, LIBRARY_VERSION, PACKAGE_VERSION, logger
