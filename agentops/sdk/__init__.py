"""
AgentOps SDK for tracing and monitoring AI agents.

This module provides a high-level API for creating and managing spans
for different types of operations in AI agent workflows.
"""

# Import core components
from agentops.sdk.core import TracingCore
from agentops.sdk.traced import TracedObject
from agentops.sdk.spanned import SpannedBase
from agentops.sdk.types import TracingConfig

# Import span types
from agentops.sdk.spans import (
    SessionSpan,
    AgentSpan,
    ToolSpan,
    CustomSpan,
)

# Import decorators
from agentops.sdk.decorators import (
    session,
    agent,
    tool,
)

__all__ = [
    # Core components
    "TracingCore",
    "TracedObject",
    "SpannedBase",
    "TracingConfig",
    
    # Span types
    "SessionSpan",
    "AgentSpan",
    "ToolSpan",
    "CustomSpan",
    
    # Decorators
    "session",
    "agent",
    "tool",
] 