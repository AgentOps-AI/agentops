"""OpenAI instrumentation wrappers.

This package contains wrapper implementations for different OpenAI API endpoints.
"""

from agentops.instrumentation.openai.wrappers.chat import handle_chat_attributes
from agentops.instrumentation.openai.wrappers.completion import handle_completion_attributes
from agentops.instrumentation.openai.wrappers.embeddings import handle_embeddings_attributes
from agentops.instrumentation.openai.wrappers.image_gen import handle_image_gen_attributes
from agentops.instrumentation.openai.wrappers.assistant import (
    handle_assistant_attributes,
    handle_run_attributes,
    handle_run_retrieve_attributes,
    handle_run_stream_attributes,
    handle_messages_attributes,
)

__all__ = [
    "handle_chat_attributes",
    "handle_completion_attributes",
    "handle_embeddings_attributes",
    "handle_image_gen_attributes",
    "handle_assistant_attributes",
    "handle_run_attributes",
    "handle_run_retrieve_attributes",
    "handle_run_stream_attributes",
    "handle_messages_attributes",
]
