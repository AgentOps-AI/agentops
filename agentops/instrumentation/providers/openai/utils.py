"""Utilities for OpenAI instrumentation.

This module provides utility functions used across the OpenAI instrumentation
components.
"""

import os
from importlib.metadata import version

from agentops.instrumentation.providers.openai.config import Config

# Get OpenAI version
try:
    _OPENAI_VERSION = version("openai")
except Exception:
    _OPENAI_VERSION = "0.0.0"


def is_openai_v1() -> bool:
    """Check if the installed OpenAI version is v1 or later."""
    return _OPENAI_VERSION >= "1.0.0"


def is_azure_openai(instance) -> bool:
    """Check if the instance is using Azure OpenAI."""
    if not is_openai_v1():
        return False

    try:
        import openai

        return isinstance(instance._client, (openai.AsyncAzureOpenAI, openai.AzureOpenAI))
    except Exception:
        return False


def is_metrics_enabled() -> bool:
    """Check if metrics collection is enabled."""
    return (os.getenv("TRACELOOP_METRICS_ENABLED") or "true").lower() == "true"


def should_record_stream_token_usage() -> bool:
    """Check if stream token usage should be recorded."""
    return Config.enrich_token_usage
