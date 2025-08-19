"""
Callback handler for sanitizing Sentry events.

This was created to address credential leaks from Supabase auth (gotrue) which
uses `TypedDict` for all internal data structures, which can be printed out
in variable extraction in Sentry events.

A long-term solution would require patching the types in the `gotrue` library
to use a sanitizable type, but that is an extensive refactor.
"""

from typing import Optional, Any


SENSITIVE_DATA_PLACEHOLDER = "[REDACTED]"

# non-exhaustive list of vars to remove from Sentry events
REMOVE_VARS = {
    "password",
    "secret",
    "token",
    "api_key",
}


def _sanitize_dictionaries(vars: dict) -> dict:
    """
    Recursively remove sensitive content from the given dictionary of variables.
    """
    for key in list(vars):
        if key.lower() in REMOVE_VARS:
            vars[key] = SENSITIVE_DATA_PLACEHOLDER
        elif isinstance(vars[key], dict):
            vars[key] = _sanitize_dictionaries(vars[key])
        elif isinstance(vars[key], list):
            # Create a new list to hold the sanitized items
            sanitized_list = []
            for i, item in enumerate(vars[key]):
                if isinstance(item, dict):
                    sanitized_list.append(_sanitize_dictionaries(item))
                else:
                    sanitized_list.append(item)
            vars[key] = sanitized_list
    return vars


def sanitize_event(event: dict[str, Any], hint: dict[str, Any]) -> Optional[dict[str, Any]]:
    if 'exception' not in event:
        return event

    for value in event["exception"].get("values", []):
        frames = value.get("stacktrace", {}).get("frames", [])
        for frame in frames:
            if frame_vars := frame.get("vars"):
                frame['vars'] = _sanitize_dictionaries(frame_vars)
    return event
