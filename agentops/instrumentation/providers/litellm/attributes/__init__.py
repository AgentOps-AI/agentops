"""Attribute extraction handlers for LiteLLM instrumentation.

This package contains specialized handlers for extracting attributes
from different types of LiteLLM operations.
"""

from agentops.instrumentation.providers.litellm.attributes.common import (
    extract_common_attributes,
    extract_error_attributes,
    extract_usage_attributes,
)
from agentops.instrumentation.providers.litellm.attributes.completion import (
    extract_completion_request_attributes,
    extract_completion_response_attributes,
)
from agentops.instrumentation.providers.litellm.attributes.embedding import (
    extract_embedding_request_attributes,
    extract_embedding_response_attributes,
)
from agentops.instrumentation.providers.litellm.attributes.streaming import (
    extract_streaming_attributes,
    aggregate_streaming_chunks,
)

__all__ = [
    # Common
    "extract_common_attributes",
    "extract_error_attributes",
    "extract_usage_attributes",
    # Completion
    "extract_completion_request_attributes",
    "extract_completion_response_attributes",
    # Embedding
    "extract_embedding_request_attributes",
    "extract_embedding_response_attributes",
    # Streaming
    "extract_streaming_attributes",
    "aggregate_streaming_chunks",
]
