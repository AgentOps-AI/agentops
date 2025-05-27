"""Version and library constants for Google ADK instrumentation."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("google-adk")
except PackageNotFoundError:
    __version__ = "0.0.0"

LIBRARY_NAME = "agentops.instrumentation.google_adk"
LIBRARY_VERSION = __version__
