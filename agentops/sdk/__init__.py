"""
AgentOps SDK for tracing and monitoring AI agents.

This module provides a high-level API for creating and managing spans
for different types of operations in AI agent workflows.
"""

# Import command functions
from agentops.sdk.commands import end_span, record, start_span

# Import core components
from agentops.sdk.core import TracingCore

# Import decorators
from agentops.sdk.decorators.agentops import agent, operation, record as record_decorator, session

# from agentops.sdk.traced import TracedObject  # Merged into TracedObject
from agentops.sdk.types import TracingConfig

# Import span types


__all__ = [
    # Core components
    "TracingCore",
    "TracingConfig",
    # Decorators
    "session",
    "operation",
    "record_decorator",
    "agent",
    # Command functions
    "start_span",
    "end_span",
    "record",
]
