"""LiteLLM instrumentor for AgentOps.

This module implements the main instrumentation logic for LiteLLM using a hybrid
approach that combines callbacks with wrapt-based instrumentation.
"""

import logging
from typing import Any, Dict, List, Optional, Set

import wrapt
from opentelemetry.trace import Span
from opentelemetry.metrics import Meter
from opentelemetry.trace import Status, StatusCode

from agentops.instrumentation.common.instrumentor import CommonInstrumentor, InstrumentorConfig
from agentops.instrumentation.providers.litellm.callback_handler import AgentOpsLiteLLMCallback
from agentops.instrumentation.providers.litellm.stream_wrapper import StreamWrapper
from agentops.instrumentation.providers.litellm.utils import detect_provider_from_model, is_streaming_response

logger = logging.getLogger(__name__)


class LiteLLMInstrumentor(CommonInstrumentor):
    """Instrumentor for LiteLLM library.

    This instrumentor uses a hybrid approach:
    1. Registers AgentOps callbacks with LiteLLM for basic integration
    2. Uses wrapt to instrument internal methods for comprehensive data collection
    3. Provides streaming support with time-to-first-token metrics
    """

    LIBRARY_NAME = "litellm"
    LIBRARY_VERSION = "1.0.0"

    def __init__(self):
        # Create configuration for CommonInstrumentor
        config = InstrumentorConfig(
            library_name=self.LIBRARY_NAME,
            library_version=self.LIBRARY_VERSION,
            wrapped_methods=[],  # We'll handle wrapping manually
            metrics_enabled=True,
            dependencies=["litellm"],
        )
        super().__init__(config)
        self._original_callbacks: Dict[str, List[Any]] = {}
        self._instrumented_methods: Set[str] = set()
        self._callback_handler: Optional[AgentOpsLiteLLMCallback] = None
        self._is_instrumented = False

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create metrics for LiteLLM instrumentation."""
        metrics = {}

        # Request counter
        metrics["request_counter"] = meter.create_counter(
            name="litellm.requests", description="Number of LiteLLM requests", unit="1"
        )

        # Token usage counter
        metrics["token_counter"] = meter.create_counter(
            name="litellm.tokens", description="Number of tokens used", unit="1"
        )

        # Request duration histogram
        metrics["duration_histogram"] = meter.create_histogram(
            name="litellm.request.duration", description="Duration of LiteLLM requests", unit="ms"
        )

        # Time to first token histogram (for streaming)
        metrics["ttft_histogram"] = meter.create_histogram(
            name="litellm.streaming.time_to_first_token",
            description="Time to first token in streaming responses",
            unit="ms",
        )

        return metrics

    def _initialize(self, **kwargs):
        """Perform custom initialization for LiteLLM."""
        try:
            import litellm

            # Step 1: Register AgentOps callbacks
            self._register_callbacks(litellm)

            # Step 2: Apply wrapt instrumentation to internal methods
            self._apply_wrapt_instrumentation(litellm)

            self._is_instrumented = True
            logger.info("LiteLLM instrumentation completed successfully")

        except Exception as e:
            logger.error(f"Failed to instrument LiteLLM: {e}")
            raise

    def _custom_unwrap(self, **kwargs):
        """Perform custom unwrapping for LiteLLM."""
        try:
            import litellm

            # Step 1: Remove callbacks
            self._unregister_callbacks(litellm)

            # Step 2: Remove wrapt instrumentation
            self._remove_wrapt_instrumentation(litellm)

            self._is_instrumented = False
            logger.info("LiteLLM instrumentation removed successfully")

        except Exception as e:
            logger.error(f"Failed to uninstrument LiteLLM: {e}")

    def _check_library_available(self) -> bool:
        """Check if LiteLLM library is available."""
        try:
            import litellm  # noqa: F401

            return True
        except ImportError:
            logger.debug("LiteLLM library not available")
            return False

    def _register_callbacks(self, litellm_module: Any) -> None:
        """Register AgentOps callbacks with LiteLLM."""
        # Store original callbacks
        self._original_callbacks["success"] = getattr(litellm_module, "success_callback", []) or []
        self._original_callbacks["failure"] = getattr(litellm_module, "failure_callback", []) or []
        self._original_callbacks["start"] = getattr(litellm_module, "start_callback", []) or []

        # Create callback handler
        self._callback_handler = AgentOpsLiteLLMCallback(self)

        # Register callbacks
        if hasattr(litellm_module, "success_callback"):
            if litellm_module.success_callback is None:
                litellm_module.success_callback = []
            if "agentops" not in litellm_module.success_callback:
                litellm_module.success_callback.append("agentops")

        if hasattr(litellm_module, "failure_callback"):
            if litellm_module.failure_callback is None:
                litellm_module.failure_callback = []
            if "agentops" not in litellm_module.failure_callback:
                litellm_module.failure_callback.append("agentops")

        if hasattr(litellm_module, "start_callback"):
            if litellm_module.start_callback is None:
                litellm_module.start_callback = []
            if "agentops" not in litellm_module.start_callback:
                litellm_module.start_callback.append("agentops")

        # Register our callback handler
        if hasattr(litellm_module, "_custom_callbacks"):
            litellm_module._custom_callbacks["agentops"] = self._callback_handler
        else:
            # Fallback for older versions
            litellm_module._custom_callbacks = {"agentops": self._callback_handler}

    def _unregister_callbacks(self, litellm_module: Any) -> None:
        """Remove AgentOps callbacks from LiteLLM."""
        # Restore original callbacks
        for callback_type, original_value in self._original_callbacks.items():
            attr_name = f"{callback_type}_callback"
            if hasattr(litellm_module, attr_name):
                setattr(litellm_module, attr_name, original_value)

        # Remove custom callback handler
        if hasattr(litellm_module, "_custom_callbacks") and "agentops" in litellm_module._custom_callbacks:
            del litellm_module._custom_callbacks["agentops"]

        self._callback_handler = None

    def _apply_wrapt_instrumentation(self, litellm_module: Any) -> None:
        """Apply wrapt instrumentation to LiteLLM methods."""
        # Apply direct wrapt wrapping for each method
        methods_to_wrap = [
            ("completion", self._wrap_completion),
            ("acompletion", self._wrap_async_completion),
            ("embedding", self._wrap_embedding),
            ("aembedding", self._wrap_async_embedding),
            ("image_generation", self._wrap_image_generation),
            ("moderation", self._wrap_moderation),
        ]

        for method_name, wrapper in methods_to_wrap:
            try:
                if hasattr(litellm_module, method_name):
                    wrapt.wrap_function_wrapper("litellm", method_name, wrapper)
                    self._instrumented_methods.add(method_name)
                    logger.debug(f"Instrumented litellm.{method_name}")
            except Exception as e:
                logger.warning(f"Failed to instrument {method_name}: {e}")

    def _remove_wrapt_instrumentation(self, litellm_module: Any) -> None:
        """Remove wrapt instrumentation from LiteLLM methods."""
        # Note: wrapt doesn't provide a direct way to unwrap, so we track what we've wrapped
        # In production, you might need to store original functions and restore them
        self._instrumented_methods.clear()

    def _wrap_completion(self, wrapped, instance, args, kwargs):
        """Wrap LiteLLM completion calls."""
        if not self._tracer:
            return wrapped(*args, **kwargs)

        # Check if this is a streaming request
        is_streaming = kwargs.get("stream", False)

        span_name = "litellm.completion"

        # Extract attributes before the call
        model = kwargs.get("model", args[0] if args else "unknown")
        provider = detect_provider_from_model(model)

        with self._tracer.start_as_current_span(span_name) as span:
            # Set basic attributes
            span.set_attribute("llm.vendor", "litellm")
            span.set_attribute("llm.request.model", model)
            span.set_attribute("llm.provider", provider)

            # Set request attributes
            if "messages" in kwargs:
                span.set_attribute("llm.request.messages_count", len(kwargs["messages"]))
            if "temperature" in kwargs:
                span.set_attribute("llm.request.temperature", kwargs["temperature"])
            if "max_tokens" in kwargs:
                span.set_attribute("llm.request.max_tokens", kwargs["max_tokens"])
            if "stream" in kwargs:
                span.set_attribute("llm.request.stream", kwargs["stream"])

            try:
                # Call the original method
                result = wrapped(*args, **kwargs)

                # Handle streaming responses
                if is_streaming and is_streaming_response(result):
                    # Check if the result is already wrapped by OpenAI instrumentor
                    if hasattr(result, "__class__") and "OpenaiStreamWrapper" in result.__class__.__name__:
                        # Already wrapped by OpenAI, don't wrap again
                        # Just end our span since OpenAI will handle the telemetry
                        logger.debug("LiteLLM: Stream already wrapped by OpenAI instrumentor, skipping our wrapper")
                        span.set_status(Status(StatusCode.OK))
                        span.end()
                        return result
                    else:
                        # Not wrapped by OpenAI, apply our wrapper
                        return StreamWrapper(result, span, self._handle_streaming_chunk, self._finalize_streaming_span)

                # Handle regular responses
                self._set_response_attributes(span, result)
                return result

            except Exception as e:
                span.record_exception(e)
                span.set_attribute("llm.error", str(e))
                raise

    async def _wrap_async_completion(self, wrapped, instance, args, kwargs):
        """Wrap async LiteLLM completion calls."""
        if not self._tracer:
            return await wrapped(*args, **kwargs)

        # Check if this is a streaming request
        is_streaming = kwargs.get("stream", False)

        span_name = "litellm.acompletion"

        # Extract attributes before the call
        model = kwargs.get("model", args[0] if args else "unknown")
        provider = detect_provider_from_model(model)

        with self._tracer.start_as_current_span(span_name) as span:
            # Set basic attributes
            span.set_attribute("llm.vendor", "litellm")
            span.set_attribute("llm.request.model", model)
            span.set_attribute("llm.provider", provider)

            # Set request attributes
            if "messages" in kwargs:
                span.set_attribute("llm.request.messages_count", len(kwargs["messages"]))
            if "temperature" in kwargs:
                span.set_attribute("llm.request.temperature", kwargs["temperature"])
            if "max_tokens" in kwargs:
                span.set_attribute("llm.request.max_tokens", kwargs["max_tokens"])
            if "stream" in kwargs:
                span.set_attribute("llm.request.stream", kwargs["stream"])

            try:
                # Call the original method
                result = await wrapped(*args, **kwargs)

                # Handle streaming responses
                if is_streaming and is_streaming_response(result):
                    # Check if the result is already wrapped by OpenAI instrumentor
                    if hasattr(result, "__class__") and "OpenaiStreamWrapper" in result.__class__.__name__:
                        # Already wrapped by OpenAI, just return it
                        logger.debug("LiteLLM: Async stream already wrapped by OpenAI instrumentor")
                        return result
                    else:
                        # For async streaming, we need an async stream wrapper
                        from agentops.instrumentation.providers.litellm.stream_wrapper import AsyncStreamWrapper

                        return AsyncStreamWrapper(
                            result, span, self._handle_streaming_chunk, self._finalize_streaming_span
                        )

                # Handle regular responses
                self._set_response_attributes(span, result)
                return result

            except Exception as e:
                span.record_exception(e)
                span.set_attribute("llm.error", str(e))
                raise

    def _wrap_embedding(self, wrapped, instance, args, kwargs):
        """Wrap LiteLLM embedding calls."""
        if not self._tracer:
            return wrapped(*args, **kwargs)

        span_name = "litellm.embedding"

        model = kwargs.get("model", args[0] if args else "unknown")
        provider = detect_provider_from_model(model)

        with self._tracer.start_as_current_span(span_name) as span:
            span.set_attribute("llm.vendor", "litellm")
            span.set_attribute("llm.request.model", model)
            span.set_attribute("llm.provider", provider)
            span.set_attribute("llm.request.type", "embedding")

            # Set input attributes
            if "input" in kwargs:
                input_data = kwargs["input"]
                if isinstance(input_data, list):
                    span.set_attribute("llm.request.input_count", len(input_data))
                else:
                    span.set_attribute("llm.request.input_count", 1)

            try:
                result = wrapped(*args, **kwargs)

                # Set response attributes
                # Handle both object and dict responses
                if isinstance(result, dict):
                    # Handle dict response format
                    if "data" in result and result["data"]:
                        span.set_attribute("llm.response.embedding_count", len(result["data"]))
                        if result["data"] and "embedding" in result["data"][0]:
                            span.set_attribute("llm.response.embedding_dim", len(result["data"][0]["embedding"]))

                    if "usage" in result:
                        usage = result["usage"]
                        if isinstance(usage, dict):
                            span.set_attribute("llm.usage.total_tokens", usage.get("total_tokens", 0))
                else:
                    # Handle object response format
                    if hasattr(result, "data") and result.data:
                        span.set_attribute("llm.response.embedding_count", len(result.data))
                        if result.data and hasattr(result.data[0], "embedding"):
                            span.set_attribute("llm.response.embedding_dim", len(result.data[0].embedding))

                    if hasattr(result, "usage"):
                        usage = result.usage
                        if isinstance(usage, dict):
                            span.set_attribute("llm.usage.total_tokens", usage.get("total_tokens", 0))
                        elif hasattr(usage, "total_tokens"):
                            span.set_attribute("llm.usage.total_tokens", usage.total_tokens)

                return result

            except Exception as e:
                span.record_exception(e)
                span.set_attribute("llm.error", str(e))
                raise

    async def _wrap_async_embedding(self, wrapped, instance, args, kwargs):
        """Wrap async LiteLLM embedding calls."""
        if not self._tracer:
            return await wrapped(*args, **kwargs)

        span_name = "litellm.aembedding"

        model = kwargs.get("model", args[0] if args else "unknown")
        provider = detect_provider_from_model(model)

        with self._tracer.start_as_current_span(span_name) as span:
            span.set_attribute("llm.vendor", "litellm")
            span.set_attribute("llm.request.model", model)
            span.set_attribute("llm.provider", provider)
            span.set_attribute("llm.request.type", "embedding")

            # Set input attributes
            if "input" in kwargs:
                input_data = kwargs["input"]
                if isinstance(input_data, list):
                    span.set_attribute("llm.request.input_count", len(input_data))
                else:
                    span.set_attribute("llm.request.input_count", 1)

            try:
                result = await wrapped(*args, **kwargs)

                # Set response attributes
                # Handle both object and dict responses
                if isinstance(result, dict):
                    # Handle dict response format
                    if "data" in result and result["data"]:
                        span.set_attribute("llm.response.embedding_count", len(result["data"]))
                        if result["data"] and "embedding" in result["data"][0]:
                            span.set_attribute("llm.response.embedding_dim", len(result["data"][0]["embedding"]))

                    if "usage" in result:
                        usage = result["usage"]
                        if isinstance(usage, dict):
                            span.set_attribute("llm.usage.total_tokens", usage.get("total_tokens", 0))
                else:
                    # Handle object response format
                    if hasattr(result, "data") and result.data:
                        span.set_attribute("llm.response.embedding_count", len(result.data))
                        if result.data and hasattr(result.data[0], "embedding"):
                            span.set_attribute("llm.response.embedding_dim", len(result.data[0].embedding))

                    if hasattr(result, "usage"):
                        usage = result.usage
                        if isinstance(usage, dict):
                            span.set_attribute("llm.usage.total_tokens", usage.get("total_tokens", 0))
                        elif hasattr(usage, "total_tokens"):
                            span.set_attribute("llm.usage.total_tokens", usage.total_tokens)

                return result

            except Exception as e:
                span.record_exception(e)
                span.set_attribute("llm.error", str(e))
                raise

    def _wrap_image_generation(self, wrapped, instance, args, kwargs):
        """Wrap LiteLLM image generation calls."""
        if not self._tracer:
            return wrapped(*args, **kwargs)

        span_name = "litellm.image_generation"

        model = kwargs.get("model", args[0] if args else "unknown")
        provider = detect_provider_from_model(model)

        with self._tracer.start_as_current_span(span_name) as span:
            span.set_attribute("llm.vendor", "litellm")
            span.set_attribute("llm.request.model", model)
            span.set_attribute("llm.provider", provider)
            span.set_attribute("llm.request.type", "image_generation")

            # Set request attributes
            if "prompt" in kwargs:
                span.set_attribute("llm.request.prompt_length", len(kwargs["prompt"]))
            if "n" in kwargs:
                span.set_attribute("llm.request.n_images", kwargs["n"])
            if "size" in kwargs:
                span.set_attribute("llm.request.image_size", kwargs["size"])

            try:
                result = wrapped(*args, **kwargs)

                # Set response attributes
                if hasattr(result, "data") and result.data:
                    span.set_attribute("llm.response.image_count", len(result.data))

                return result

            except Exception as e:
                span.record_exception(e)
                span.set_attribute("llm.error", str(e))
                raise

    def _wrap_moderation(self, wrapped, instance, args, kwargs):
        """Wrap LiteLLM moderation calls."""
        if not self._tracer:
            return wrapped(*args, **kwargs)

        span_name = "litellm.moderation"

        model = kwargs.get("model", args[0] if args else "unknown")
        provider = detect_provider_from_model(model)

        with self._tracer.start_as_current_span(span_name) as span:
            span.set_attribute("llm.vendor", "litellm")
            span.set_attribute("llm.request.model", model)
            span.set_attribute("llm.provider", provider)
            span.set_attribute("llm.request.type", "moderation")

            # Set request attributes
            if "input" in kwargs:
                input_data = kwargs["input"]
                if isinstance(input_data, list):
                    span.set_attribute("llm.request.input_count", len(input_data))
                else:
                    span.set_attribute("llm.request.input_count", 1)

            try:
                result = wrapped(*args, **kwargs)

                # Set response attributes
                if hasattr(result, "results") and result.results:
                    span.set_attribute("llm.response.results_count", len(result.results))
                    # Check if any content was flagged
                    flagged_count = sum(1 for r in result.results if r.get("flagged", False))
                    span.set_attribute("llm.response.flagged_count", flagged_count)

                return result

            except Exception as e:
                span.record_exception(e)
                span.set_attribute("llm.error", str(e))
                raise

    def _set_response_attributes(self, span: Span, response: Any) -> None:
        """Set response attributes on the span."""
        if hasattr(response, "choices") and response.choices:
            span.set_attribute("llm.response.choices_count", len(response.choices))

            # Get first choice details
            first_choice = response.choices[0]
            if hasattr(first_choice, "message"):
                if hasattr(first_choice.message, "content"):
                    content = first_choice.message.content
                    if content:
                        span.set_attribute("llm.response.content_length", len(content))
                if hasattr(first_choice.message, "function_call"):
                    span.set_attribute("llm.response.has_function_call", True)
                if hasattr(first_choice.message, "tool_calls") and first_choice.message.tool_calls:
                    span.set_attribute("llm.response.tool_calls_count", len(first_choice.message.tool_calls))

            if hasattr(first_choice, "finish_reason"):
                span.set_attribute("llm.response.finish_reason", first_choice.finish_reason)

        # Set usage attributes
        if hasattr(response, "usage"):
            usage = response.usage
            if hasattr(usage, "prompt_tokens"):
                span.set_attribute("llm.usage.prompt_tokens", usage.prompt_tokens)
            if hasattr(usage, "completion_tokens"):
                span.set_attribute("llm.usage.completion_tokens", usage.completion_tokens)
            if hasattr(usage, "total_tokens"):
                span.set_attribute("llm.usage.total_tokens", usage.total_tokens)

        # Set model info from response
        if hasattr(response, "model"):
            span.set_attribute("llm.response.model", response.model)

        # Set response ID
        if hasattr(response, "id"):
            span.set_attribute("llm.response.id", response.id)

    def _handle_streaming_chunk(self, span: Span, chunk: Any, is_first: bool) -> None:
        """Handle a streaming chunk."""
        if is_first:
            span.set_attribute("llm.response.first_token_time", True)

        # Track chunk details
        if hasattr(chunk, "choices") and chunk.choices:
            for choice in chunk.choices:
                if hasattr(choice, "delta"):
                    delta = choice.delta
                    if hasattr(delta, "content") and delta.content:
                        # Could track content length, but be careful with performance
                        pass
                    if hasattr(delta, "function_call"):
                        span.set_attribute("llm.response.has_function_call", True)
                    if hasattr(delta, "tool_calls"):
                        span.set_attribute("llm.response.has_tool_calls", True)

    def _finalize_streaming_span(self, span: Span, chunks: List[Any]) -> None:
        """Finalize a streaming span with aggregated data."""
        span.set_attribute("llm.response.chunk_count", len(chunks))

        # Aggregate usage if available
        total_tokens = 0
        for chunk in chunks:
            if hasattr(chunk, "usage") and chunk.usage:
                if hasattr(chunk.usage, "total_tokens"):
                    total_tokens += chunk.usage.total_tokens

        if total_tokens > 0:
            span.set_attribute("llm.usage.total_tokens", total_tokens)
