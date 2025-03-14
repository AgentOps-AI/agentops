from typing import Any


def is_coroutine_or_generator(fn: Any) -> bool:
    """Check if a function is asynchronous (coroutine or async generator)"""
    import inspect

    return inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn)
