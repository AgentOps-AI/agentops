"""Anthropic API instrumentation.

This module provides instrumentation for the Anthropic API,
including chat completions, streaming, and event handling.
"""

from agentops.instrumentation.common.constants import setup_instrumentation_module

# Setup standard instrumentation components
LIBRARY_NAME, LIBRARY_VERSION, PACKAGE_VERSION, logger = setup_instrumentation_module(
    library_name="anthropic", library_version="1.0.0", package_name="anthropic", display_name="Anthropic SDK"
)

# Import after defining constants to avoid circular imports
from agentops.instrumentation.providers.anthropic.instrumentor import AnthropicInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "PACKAGE_VERSION",
    "AnthropicInstrumentor",
]
