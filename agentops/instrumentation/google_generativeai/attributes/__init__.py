"""Attribute extractors for Google Generative AI instrumentation."""

from agentops.instrumentation.google_generativeai.attributes.common import (
    get_common_instrumentation_attributes,
    extract_request_attributes,
)
from agentops.instrumentation.google_generativeai.attributes.model import (
    get_model_attributes,
    get_generate_content_attributes,
    get_stream_attributes,
    get_token_counting_attributes,
)
from agentops.instrumentation.google_generativeai.attributes.chat import (
    get_chat_attributes,
)

__all__ = [
    "get_common_instrumentation_attributes",
    "extract_request_attributes",
    "get_model_attributes",
    "get_generate_content_attributes",
    "get_stream_attributes",
    "get_chat_attributes",
    "get_token_counting_attributes",
]
