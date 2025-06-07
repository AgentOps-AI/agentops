"""Shared utilities for OpenAI instrumentation wrappers.

This module contains common functions and utilities used across different
OpenAI API endpoint wrappers.
"""

import os
import types
import logging
from typing import Any, Dict, Optional
from importlib.metadata import version

import openai
from opentelemetry import context as context_api

from agentops.instrumentation.openai.utils import is_openai_v1

logger = logging.getLogger(__name__)

# Pydantic version for model serialization
_PYDANTIC_VERSION = version("pydantic")

# Cache for tiktoken encodings
tiktoken_encodings = {}


def should_send_prompts() -> bool:
    """Check if prompt content should be sent in traces."""
    return (os.getenv("TRACELOOP_TRACE_CONTENT") or "true").lower() == "true" or context_api.get_value(
        "override_enable_content_tracing"
    )


def is_streaming_response(response: Any) -> bool:
    """Check if a response is a streaming response."""
    if is_openai_v1():
        return isinstance(response, openai.Stream) or isinstance(response, openai.AsyncStream)
    return isinstance(response, types.GeneratorType) or isinstance(response, types.AsyncGeneratorType)


def model_as_dict(model: Any) -> Dict[str, Any]:
    """Convert a model object to a dictionary."""
    if model is None:
        return {}
    if isinstance(model, dict):
        return model
    if _PYDANTIC_VERSION < "2.0.0":
        return model.dict()
    if hasattr(model, "model_dump"):
        return model.model_dump()
    elif hasattr(model, "parse"):  # Raw API response
        return model_as_dict(model.parse())
    else:
        return model if isinstance(model, dict) else {}


def get_token_count_from_string(string: str, model_name: str) -> Optional[int]:
    """Get token count from a string using tiktoken."""
    from agentops.instrumentation.openai.utils import should_record_stream_token_usage

    if not should_record_stream_token_usage():
        return None

    try:
        import tiktoken
    except ImportError:
        return None

    if tiktoken_encodings.get(model_name) is None:
        try:
            encoding = tiktoken.encoding_for_model(model_name)
        except KeyError as ex:
            logger.warning(f"Failed to get tiktoken encoding for model_name {model_name}, error: {str(ex)}")
            return None

        tiktoken_encodings[model_name] = encoding
    else:
        encoding = tiktoken_encodings.get(model_name)

    token_count = len(encoding.encode(string))
    return token_count
