
"""
Decorators for instrumenting code with AgentOps.

This module provides a simplified set of decorators for instrumenting functions
and methods with appropriate span kinds. Decorators can be used with or without parentheses.
"""
import inspect
from typing import (Any, Callable, Optional, Type, TypeVar, Union, cast,
                    overload)

import wrapt

from agentops.sdk.decorators.wrappers import wrap_class, wrap_method
from agentops.semconv.span_kinds import SpanKind

# Type variables for better type hinting
F = TypeVar("F", bound=Callable[..., Any])
C = TypeVar("C", bound=Type)


def task(
    name: Optional[str] = None,
    version: Optional[int] = None,
    method_name: Optional[str] = None,
    entity_kind=SpanKind.TASK,
):
    if method_name is None:
        return wrap_method(name=name, version=version, entity_kind=entity_kind)
    else:
        return wrap_class(
            name=name,
            version=version,
            method_name=method_name,
            entity_kind=entity_kind,
        )


def workflow(
    name: Optional[str] = None,
    version: Optional[int] = None,
    method_name: Optional[str] = None,
    entity_kind=SpanKind.WORKFLOW,
):
    if method_name is None:
        return wrap_method(name=name, version=version, entity_kind=entity_kind)
    else:
        return wrap_class(
            name=name,
            version=version,
            method_name=method_name,
            entity_kind=entity_kind,
        )


def agent(
    name: Optional[str] = None,
    version: Optional[int] = None,
    method_name: Optional[str] = None,
):
    if method_name is None:
        return wrap_method(name=name, version=version, entity_kind=SpanKind.AGENT)
    else:
        return wrap_class(
            name=name,
            version=version,
            method_name=method_name,
            entity_kind=SpanKind.AGENT,
        )


def tool(
    name: Optional[str] = None,
    version: Optional[int] = None,
    method_name: Optional[str] = None,
):
    return task(
        name=name,
        version=version,
        method_name=method_name,
        entity_kind=SpanKind.TOOL,
    )


def session(
    name: Optional[str] = None,
    version: Optional[int] = None,
    method_name: Optional[str] = None,
):
    if method_name is None:
        return wrap_method(name=name, version=version, entity_kind=SpanKind.SESSION)
    else:
        return wrap_class(
            name=name,
            version=version,
            method_name=method_name,
            entity_kind=SpanKind.SESSION,
        )


operation = task