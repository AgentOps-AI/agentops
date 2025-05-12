"""
Decorators for instrumenting code with AgentOps.

This module provides a simplified set of decorators for instrumenting functions
and methods with appropriate span kinds. Decorators can be used with or without parentheses.
"""

from agentops.sdk.decorators.factory import create_entity_decorator
from agentops.semconv.span_kinds import SpanKind

# Create decorators for specific entity types using the factory
agent = create_entity_decorator(SpanKind.AGENT)
task = create_entity_decorator(SpanKind.TASK)
operation = create_entity_decorator(SpanKind.OPERATION)
workflow = create_entity_decorator(SpanKind.WORKFLOW)
session = create_entity_decorator(SpanKind.SESSION)
operation = task

__all__ = ["agent", "task", "workflow", "session", "operation"]

# Create decorators task, workflow, session, agent
