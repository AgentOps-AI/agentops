"""Configuration for OpenAI instrumentation.

This module provides a global configuration object that can be used to customize
the behavior of OpenAI instrumentation across all components.
"""

from typing import Callable, Optional, Dict
from typing_extensions import Protocol


class UploadImageCallable(Protocol):
    """Protocol for the upload_base64_image function."""

    async def __call__(self, trace_id: str, span_id: str, image_name: str, base64_string: str) -> str:
        """Upload a base64 image and return the URL."""
        ...


class Config:
    """Global configuration for OpenAI instrumentation.

    Attributes:
        enrich_token_usage: Whether to calculate token usage for streaming responses
        enrich_assistant: Whether to enrich assistant responses with additional data
        exception_logger: Optional function to log exceptions
        get_common_metrics_attributes: Function to get common attributes for metrics
        upload_base64_image: Optional async function to upload base64 images
        enable_trace_context_propagation: Whether to propagate trace context in headers
    """

    enrich_token_usage: bool = True
    enrich_assistant: bool = True
    exception_logger: Optional[Callable[[Exception], None]] = None
    get_common_metrics_attributes: Callable[[], Dict[str, str]] = lambda: {}
    upload_base64_image: Optional[UploadImageCallable] = None
    enable_trace_context_propagation: bool = True
