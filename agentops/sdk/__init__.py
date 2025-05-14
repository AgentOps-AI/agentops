"""
AgentOps SDK for tracing and monitoring AI agents.

This module provides a high-level API for creating and managing spans
for different types of operations in AI agent workflows.
"""

# Import core components
from agentops.sdk.core import TracingCore

# Import decorators
from agentops.sdk.decorators import agent, operation, session, task, workflow

# from agentops.sdk.traced import TracedObject  # Merged into TracedObject
from agentops.sdk.types import TracingConfig

__all__ = [
    # Core components
    "TracingCore",
    "TracingConfig",
    # Decorators
    "session",
    "operation",
    "agent",
    "task",
    "workflow",
]
