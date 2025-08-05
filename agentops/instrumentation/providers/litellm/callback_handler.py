"""LiteLLM callback handler for AgentOps.

This module implements the callback handler that integrates with LiteLLM's
callback system to capture telemetry data.
"""

import logging
import time
from typing import Any, Dict, Optional

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from agentops.instrumentation.providers.litellm.utils import (
    detect_provider_from_model,
    extract_model_info,
    safe_get_attribute,
)

logger = logging.getLogger(__name__)


class AgentOpsLiteLLMCallback:
    """Callback handler for LiteLLM that integrates with AgentOps.

    This handler is registered with LiteLLM's callback system and captures
    telemetry data for all LLM operations. It works in conjunction with
    the wrapt instrumentation for comprehensive data collection.
    """

    def __init__(self, instrumentor):
        """Initialize the callback handler.

        Args:
            instrumentor: The LiteLLMInstrumentor instance
        """
        self.instrumentor = instrumentor
        self.tracer = trace.get_tracer(__name__)
        self._active_spans: Dict[str, Any] = {}
        self._start_times: Dict[str, float] = {}

    def log_pre_api_call(self, model: str, messages: list, kwargs: Dict[str, Any]) -> None:
        """Called before the API call is made.

        This is the 'start' callback in LiteLLM.
        """
        try:
            # Generate a unique ID for this request
            request_id = kwargs.get("litellm_call_id", str(time.time()))

            # Start timing
            self._start_times[request_id] = time.time()

            # Create span if not already created by wrapt
            span = trace.get_current_span()
            if not span.is_recording():
                # Create a new span if wrapt didn't create one
                span = self.tracer.start_span("litellm.callback.completion")
                self._active_spans[request_id] = span

            # Extract provider and model info
            provider = detect_provider_from_model(model)
            model_info = extract_model_info(model)

            # Set attributes
            span.set_attribute("llm.vendor", "litellm")
            span.set_attribute("llm.provider", provider)
            span.set_attribute("llm.request.model", model)
            span.set_attribute("llm.request.model_family", model_info.get("family", "unknown"))

            # Message attributes
            if messages:
                span.set_attribute("llm.request.messages_count", len(messages))

                # Analyze message types
                message_types = {}
                total_content_length = 0

                for msg in messages:
                    role = msg.get("role", "unknown")
                    message_types[role] = message_types.get(role, 0) + 1

                    content = msg.get("content", "")
                    if isinstance(content, str):
                        total_content_length += len(content)
                    elif isinstance(content, list):
                        # Handle multi-modal content
                        for item in content:
                            if isinstance(item, dict) and "text" in item:
                                total_content_length += len(item["text"])

                for role, count in message_types.items():
                    span.set_attribute(f"llm.request.messages.{role}_count", count)

                span.set_attribute("llm.request.total_content_length", total_content_length)

            # Request parameters
            for param in [
                "temperature",
                "max_tokens",
                "top_p",
                "frequency_penalty",
                "presence_penalty",
                "stop",
                "n",
                "stream",
                "logprobs",
            ]:
                if param in kwargs:
                    value = kwargs[param]
                    if value is not None:
                        span.set_attribute(f"llm.request.{param}", value)

            # Function/Tool calling
            if "functions" in kwargs:
                span.set_attribute("llm.request.functions_count", len(kwargs["functions"]))
            if "tools" in kwargs:
                span.set_attribute("llm.request.tools_count", len(kwargs["tools"]))
            if "function_call" in kwargs:
                span.set_attribute("llm.request.function_call", str(kwargs["function_call"]))
            if "tool_choice" in kwargs:
                span.set_attribute("llm.request.tool_choice", str(kwargs["tool_choice"]))

            # Custom metadata
            if "metadata" in kwargs:
                for key, value in kwargs["metadata"].items():
                    if isinstance(value, (str, int, float, bool)):
                        span.set_attribute(f"llm.metadata.{key}", value)

            logger.debug(f"Pre-API call logged for {model} (request_id: {request_id})")

        except Exception as e:
            logger.error(f"Error in log_pre_api_call: {e}")

    def log_success_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float) -> None:
        """Called when the API call succeeds.

        This is the 'success' callback in LiteLLM.
        """
        try:
            request_id = kwargs.get("litellm_call_id", str(start_time))

            # Get the span (either from wrapt or our own)
            span = self._active_spans.get(request_id) or trace.get_current_span()

            if span.is_recording():
                # Calculate duration
                duration = end_time - start_time
                span.set_attribute("llm.response.duration_seconds", duration)

                # Response attributes
                if hasattr(response_obj, "id"):
                    span.set_attribute("llm.response.id", response_obj.id)

                if hasattr(response_obj, "model"):
                    span.set_attribute("llm.response.model", response_obj.model)

                if hasattr(response_obj, "created"):
                    span.set_attribute("llm.response.created", response_obj.created)

                # Choices
                if hasattr(response_obj, "choices") and response_obj.choices:
                    span.set_attribute("llm.response.choices_count", len(response_obj.choices))

                    first_choice = response_obj.choices[0]

                    # Finish reason
                    finish_reason = safe_get_attribute(first_choice, "finish_reason")
                    if finish_reason:
                        span.set_attribute("llm.response.finish_reason", finish_reason)

                    # Message content
                    message = safe_get_attribute(first_choice, "message")
                    if message:
                        content = safe_get_attribute(message, "content")
                        if content:
                            span.set_attribute("llm.response.content_length", len(content))

                        # Function call
                        function_call = safe_get_attribute(message, "function_call")
                        if function_call:
                            span.set_attribute("llm.response.has_function_call", True)
                            if hasattr(function_call, "name"):
                                span.set_attribute("llm.response.function_name", function_call.name)

                        # Tool calls
                        tool_calls = safe_get_attribute(message, "tool_calls")
                        if tool_calls:
                            span.set_attribute("llm.response.tool_calls_count", len(tool_calls))
                            tool_names = [
                                tc.function.name
                                for tc in tool_calls
                                if hasattr(tc, "function") and hasattr(tc.function, "name")
                            ]
                            if tool_names:
                                span.set_attribute("llm.response.tool_names", ",".join(tool_names))

                # Usage information
                usage = safe_get_attribute(response_obj, "usage")
                if usage:
                    for attr in ["prompt_tokens", "completion_tokens", "total_tokens"]:
                        value = safe_get_attribute(usage, attr)
                        if value is not None:
                            span.set_attribute(f"llm.usage.{attr}", value)

                    # Calculate cost if possible
                    if hasattr(usage, "prompt_tokens") and hasattr(usage, "completion_tokens"):
                        model = kwargs.get("model", "")
                        cost = self._calculate_cost(model, usage.prompt_tokens, usage.completion_tokens)
                        if cost:
                            span.set_attribute("llm.usage.estimated_cost", cost)

                # Set success status
                span.set_status(Status(StatusCode.OK))

                # End span if we created it
                if request_id in self._active_spans:
                    span.end()
                    del self._active_spans[request_id]

            # Clean up
            if request_id in self._start_times:
                del self._start_times[request_id]

            logger.debug(f"Success event logged (request_id: {request_id})")

        except Exception as e:
            logger.error(f"Error in log_success_event: {e}")

    def log_failure_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float) -> None:
        """Called when the API call fails.

        This is the 'failure' callback in LiteLLM.
        """
        try:
            request_id = kwargs.get("litellm_call_id", str(start_time))

            # Get the span
            span = self._active_spans.get(request_id) or trace.get_current_span()

            if span.is_recording():
                # Calculate duration
                duration = end_time - start_time
                span.set_attribute("llm.response.duration_seconds", duration)

                # Error information
                if isinstance(response_obj, Exception):
                    span.record_exception(response_obj)
                    span.set_attribute("llm.error.type", type(response_obj).__name__)
                    span.set_attribute("llm.error.message", str(response_obj))

                    # Extract specific error details
                    if hasattr(response_obj, "status_code"):
                        span.set_attribute("llm.error.status_code", response_obj.status_code)
                    if hasattr(response_obj, "llm_provider"):
                        span.set_attribute("llm.error.provider", response_obj.llm_provider)
                    if hasattr(response_obj, "model"):
                        span.set_attribute("llm.error.model", response_obj.model)

                # Set error status
                span.set_status(Status(StatusCode.ERROR, str(response_obj)))

                # End span if we created it
                if request_id in self._active_spans:
                    span.end()
                    del self._active_spans[request_id]

            # Clean up
            if request_id in self._start_times:
                del self._start_times[request_id]

            logger.debug(f"Failure event logged (request_id: {request_id})")

        except Exception as e:
            logger.error(f"Error in log_failure_event: {e}")

    def log_stream_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float) -> None:
        """Called for streaming responses.

        This can be called multiple times for a single request.
        """
        try:
            request_id = kwargs.get("litellm_call_id", str(start_time))

            # Get the span
            span = self._active_spans.get(request_id) or trace.get_current_span()

            if span.is_recording():
                # Track streaming metrics
                if not span.attributes.get("llm.response.is_streaming"):
                    span.set_attribute("llm.response.is_streaming", True)
                    span.set_attribute("llm.response.first_chunk_time", end_time - start_time)

                # Note: Detailed chunk handling is done in the stream wrapper

            logger.debug(f"Stream event logged (request_id: {request_id})")

        except Exception as e:
            logger.error(f"Error in log_stream_event: {e}")

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> Optional[float]:
        """Calculate estimated cost based on model and token usage.

        This is a simplified version - in production, you'd want to maintain
        a comprehensive pricing table.
        """
        # Simplified pricing table (in USD per 1K tokens)
        pricing = {
            # OpenAI
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-32k": {"prompt": 0.06, "completion": 0.12},
            "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
            "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004},
            # Anthropic
            "claude-2": {"prompt": 0.008, "completion": 0.024},
            "claude-instant": {"prompt": 0.0008, "completion": 0.0024},
            # Add more models as needed
        }

        # Extract base model name
        base_model = model.lower()
        for model_key in pricing:
            if model_key in base_model:
                rates = pricing[model_key]
                cost = (prompt_tokens * rates["prompt"] / 1000) + (completion_tokens * rates["completion"] / 1000)
                return round(cost, 6)

        return None

    # LiteLLM callback interface methods
    async def async_log_success_event(
        self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float
    ) -> None:
        """Async version of log_success_event."""
        self.log_success_event(kwargs, response_obj, start_time, end_time)

    async def async_log_failure_event(
        self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float
    ) -> None:
        """Async version of log_failure_event."""
        self.log_failure_event(kwargs, response_obj, start_time, end_time)

    async def async_log_stream_event(
        self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float
    ) -> None:
        """Async version of log_stream_event."""
        self.log_stream_event(kwargs, response_obj, start_time, end_time)

    async def async_pre_call_hook(
        self, user_api_key_dict: Dict[str, Any], cache: Any, data: Dict[str, Any], call_type: str
    ) -> Dict[str, Any]:
        """Async pre-call hook for modifying request data."""
        # We don't modify the request, just return as-is
        return data

    async def async_post_call_success_hook(
        self, data: Dict[str, Any], user_api_key_dict: Dict[str, Any], response: Any
    ) -> Any:
        """Async post-call success hook."""
        # We don't modify the response, just return as-is
        return response

    async def async_post_call_failure_hook(
        self, exception: Exception, traceback_exception: Any, user_api_key_dict: Dict[str, Any]
    ) -> None:
        """Async post-call failure hook."""
        # We just observe, don't modify
        pass
