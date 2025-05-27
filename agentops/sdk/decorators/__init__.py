"""
Decorators for instrumenting code with AgentOps.
Provides @trace for creating trace-level spans (sessions) and other decorators for nested spans.
"""

import functools
from termcolor import colored

from agentops.logging import logger
from agentops.sdk.decorators.factory import create_entity_decorator
from agentops.semconv.span_kinds import SpanKind

# Create decorators for specific entity types using the factory
agent = create_entity_decorator(SpanKind.AGENT)
task = create_entity_decorator(SpanKind.TASK)
operation_decorator = create_entity_decorator(SpanKind.OPERATION)
workflow = create_entity_decorator(SpanKind.WORKFLOW)
trace = create_entity_decorator(SpanKind.SESSION)
session = create_entity_decorator(SpanKind.SESSION)
tool = create_entity_decorator(SpanKind.TOOL)
operation = task

# For backward compatibility: @session decorator calls @trace decorator
@functools.wraps(trace)
def session(*args, **kwargs):
    """@deprecated Use @agentops.trace instead. Wraps the @trace decorator for backward compatibility."""
    logger.info(colored("@agentops.session decorator is deprecated. Please use @agentops.trace instead.", "yellow"))
    # If called as @session or @session(...)
    if not args or not callable(args[0]):  # called with kwargs like @session(name=...)
        return trace(*args, **kwargs)
    else:  # called as @session directly on a function
        return trace(args[0], **kwargs)  # args[0] is the wrapped function


# Note: The original `operation = task` was potentially problematic if `operation` was meant to be distinct.
# Using operation_decorator for clarity if a distinct OPERATION kind decorator is needed.
# For now, keeping the alias as it was, assuming it was intentional for `operation` to be `task`.
operation = task

__all__ = ["agent", "task", "workflow", "trace", "session", "operation", "tool"]
