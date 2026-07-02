"""
LiteLLM callback handler for AgentOps.

This module provides the LiteLLM callback handler for AgentOps tracing and monitoring.
It handles both completion and responses API calls across all LiteLLM-supported providers
including OpenAI, Anthropic, and others.

Usage:
    from agentops.integration.callbacks.litellm import LiteLLMCallbackHandler
    import litellm
    
    handler = LiteLLMCallbackHandler(api_key="your-api-key")
    litellm.callbacks = [handler]
    
    # Or use the string-based callback registration (after importing agentops)
    import agentops
    agentops.init()
    litellm.success_callback = ["agentops"]
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from opentelemetry import trace
from opentelemetry.context import attach, detach
from opentelemetry.trace import set_span_in_context
from opentelemetry.sdk.trace import Span as SDKSpan

from agentops.helpers.serialization import safe_serialize
from agentops.logging import logger
from agentops.sdk.core import tracer
from agentops.semconv import SpanKind, SpanAttributes, AgentOpsSpanKindValues

try:
    from litellm.integrations.custom_logger import CustomLogger
except ImportError:
    # Create a stub class if litellm is not installed
    class CustomLogger:
        pass


class LiteLLMCallbackHandler(CustomLogger):
    """
    AgentOps callback handler for LiteLLM.

    This handler creates spans for LLM calls made through LiteLLM, supporting
    all providers (OpenAI, Anthropic, etc.) including both completion and
    responses API calls.

    Args:
        api_key (str, optional): AgentOps API key
        tags (List[str], optional): Tags to add to the session
        auto_session (bool, optional): Whether to automatically create a session span
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        tags: Optional[List[str]] = None,
        auto_session: bool = True,
    ):
        """Initialize the callback handler."""
        super().__init__()
        self.active_spans: Dict[str, SDKSpan] = {}
        self.api_key = api_key
        self.tags = tags or []
        self.session_span = None
        self.session_token = None
        self.context_tokens: Dict[str, Any] = {}

        # Initialize AgentOps
        if auto_session:
            self._initialize_agentops()

    def _initialize_agentops(self):
        """Initialize AgentOps if not already initialized."""
        import agentops

        if not tracer.initialized:
            init_kwargs = {
                "auto_start_session": False,
                "instrument_llm_calls": False,  # We handle LLM calls via callback
            }

            if self.api_key:
                init_kwargs["api_key"] = self.api_key

            agentops.init(**init_kwargs)
            logger.debug("AgentOps initialized from LiteLLM callback handler")

        if not tracer.initialized:
            logger.warning("AgentOps not initialized, session span will not be created")
            return

        otel_tracer = tracer.get_tracer()

        span_name = f"session.{SpanKind.SESSION}"

        attributes = {
            SpanAttributes.AGENTOPS_SPAN_KIND: SpanKind.SESSION,
            "session.tags": self.tags,
            "agentops.operation.name": "session",
            "span.kind": SpanKind.SESSION,
        }

        # Create a root session span
        self.session_span = otel_tracer.start_span(span_name, attributes=attributes)

        # Attach session span to the current context
        self.session_token = attach(set_span_in_context(self.session_span))

        logger.debug("Created session span as root span for LiteLLM")

    def _get_call_id(self, kwargs: Dict[str, Any]) -> str:
        """Generate a unique call ID for tracking spans."""
        litellm_call_id = kwargs.get("litellm_call_id", "")
        if litellm_call_id:
            return str(litellm_call_id)
        # Fallback to a combination of model and timestamp
        model = kwargs.get("model", "unknown")
        return f"{model}_{id(kwargs)}"

    def _extract_provider(self, model: str) -> str:
        """Extract the provider from the model string."""
        if "/" in model:
            return model.split("/")[0]
        # Default provider mapping based on common model names
        model_lower = model.lower()
        if "claude" in model_lower:
            return "anthropic"
        elif "gpt" in model_lower or "o1" in model_lower:
            return "openai"
        elif "gemini" in model_lower:
            return "google"
        elif "mistral" in model_lower or "mixtral" in model_lower:
            return "mistral"
        elif "command" in model_lower:
            return "cohere"
        return "unknown"

    def _create_span(
        self,
        call_id: str,
        model: str,
        messages: Optional[List[Dict[str, Any]]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Optional[SDKSpan]:
        """Create a span for an LLM call."""
        if not tracer.initialized:
            logger.debug("Tracer not initialized, skipping span creation")
            return None

        otel_tracer = tracer.get_tracer()
        provider = self._extract_provider(model)
        
        span_name = f"litellm.{provider}.{model.replace('/', '_')}"

        attributes: Dict[str, Any] = {
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.LLM.value,
            "agentops.operation.name": "llm_call",
            "gen_ai.system": provider,
            "gen_ai.request.model": model,
            "litellm.provider": provider,
        }

        # Add input messages if available
        if messages:
            try:
                for i, msg in enumerate(messages):
                    if isinstance(msg, dict):
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")
                        attributes[f"gen_ai.prompt.{i}.role"] = str(role)
                        if content:
                            attributes[f"gen_ai.prompt.{i}.content"] = safe_serialize(content)[:1000]
            except Exception as e:
                logger.debug(f"Failed to extract messages: {e}")

        # Add additional kwargs
        if kwargs:
            if "temperature" in kwargs:
                attributes["gen_ai.request.temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                attributes["gen_ai.request.max_tokens"] = kwargs["max_tokens"]
            if "top_p" in kwargs:
                attributes["gen_ai.request.top_p"] = kwargs["top_p"]

        # Create span with parent context
        if self.session_span:
            parent_ctx = set_span_in_context(self.session_span)
            span = otel_tracer.start_span(span_name, context=parent_ctx, attributes=attributes)
        else:
            span = otel_tracer.start_span(span_name, attributes=attributes)

        if isinstance(span, SDKSpan):
            self.active_spans[call_id] = span
            token = attach(set_span_in_context(span))
            self.context_tokens[call_id] = token

        return span

    def _end_span(
        self,
        call_id: str,
        response_obj: Any = None,
        kwargs: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
    ):
        """End a span for an LLM call."""
        if call_id not in self.active_spans:
            return

        span = self.active_spans.pop(call_id)
        token = self.context_tokens.pop(call_id, None)

        try:
            # Add response attributes
            if response_obj:
                # Handle different response types
                if hasattr(response_obj, "model"):
                    span.set_attribute("gen_ai.response.model", str(response_obj.model))
                
                # Extract usage information
                usage = None
                if hasattr(response_obj, "usage") and response_obj.usage:
                    usage = response_obj.usage
                elif isinstance(response_obj, dict) and "usage" in response_obj:
                    usage = response_obj["usage"]

                if usage:
                    if hasattr(usage, "prompt_tokens"):
                        span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, usage.prompt_tokens)
                    elif isinstance(usage, dict) and "prompt_tokens" in usage:
                        span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, usage["prompt_tokens"])
                    elif isinstance(usage, dict) and "input_tokens" in usage:
                        span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, usage["input_tokens"])
                    
                    if hasattr(usage, "completion_tokens"):
                        span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, usage.completion_tokens)
                    elif isinstance(usage, dict) and "completion_tokens" in usage:
                        span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, usage["completion_tokens"])
                    elif isinstance(usage, dict) and "output_tokens" in usage:
                        span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, usage["output_tokens"])
                    
                    if hasattr(usage, "total_tokens"):
                        span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, usage.total_tokens)
                    elif isinstance(usage, dict) and "total_tokens" in usage:
                        span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, usage["total_tokens"])

                # Extract completion content
                choices = None
                if hasattr(response_obj, "choices"):
                    choices = response_obj.choices
                elif isinstance(response_obj, dict) and "choices" in response_obj:
                    choices = response_obj["choices"]
                
                # Handle responses API format (output instead of choices)
                output = None
                if hasattr(response_obj, "output"):
                    output = response_obj.output
                elif isinstance(response_obj, dict) and "output" in response_obj:
                    output = response_obj["output"]

                if choices:
                    for i, choice in enumerate(choices):
                        try:
                            message = choice.message if hasattr(choice, "message") else choice.get("message", {})
                            if message:
                                role = message.role if hasattr(message, "role") else message.get("role", "assistant")
                                content = message.content if hasattr(message, "content") else message.get("content", "")
                                span.set_attribute(f"gen_ai.completion.{i}.role", str(role))
                                if content:
                                    span.set_attribute(f"gen_ai.completion.{i}.content", str(content)[:1000])
                                
                                # Handle finish reason
                                finish_reason = choice.finish_reason if hasattr(choice, "finish_reason") else choice.get("finish_reason")
                                if finish_reason:
                                    span.set_attribute(f"gen_ai.completion.{i}.finish_reason", str(finish_reason))
                        except Exception as e:
                            logger.debug(f"Failed to extract choice {i}: {e}")
                elif output:
                    # Handle responses API format
                    for i, item in enumerate(output if isinstance(output, list) else [output]):
                        try:
                            if hasattr(item, "content"):
                                content = item.content
                            elif isinstance(item, dict):
                                content = item.get("content", item.get("text", ""))
                            else:
                                content = str(item)
                            
                            if content:
                                # Handle content that's a list of content blocks
                                if isinstance(content, list):
                                    text_parts = []
                                    for block in content:
                                        if isinstance(block, dict) and "text" in block:
                                            text_parts.append(block["text"])
                                        elif hasattr(block, "text"):
                                            text_parts.append(block.text)
                                    content = " ".join(text_parts)
                                
                                span.set_attribute(f"gen_ai.completion.{i}.content", str(content)[:1000])
                        except Exception as e:
                            logger.debug(f"Failed to extract output {i}: {e}")

            # Add cost information if available
            if kwargs and "response_cost" in kwargs:
                span.set_attribute("gen_ai.usage.cost", kwargs["response_cost"])

            # Handle exception
            if exception:
                span.record_exception(exception)
                span.set_attribute("error.type", type(exception).__name__)
                span.set_attribute("error.message", str(exception))

        except Exception as e:
            logger.warning(f"Error setting span attributes: {e}")

        # Detach context and end span
        if token:
            detach(token)

        try:
            span.end()
        except Exception as e:
            logger.warning(f"Error ending span: {e}")

    # LiteLLM CustomLogger interface methods

    def log_pre_api_call(self, model: str, messages: List[Dict[str, Any]], kwargs: Dict[str, Any]):
        """Called before an API call is made."""
        call_id = self._get_call_id(kwargs)
        self._create_span(call_id, model, messages, kwargs)
        logger.debug(f"LiteLLM pre-API call: model={model}, call_id={call_id}")

    def log_post_api_call(self, kwargs: Dict[str, Any], response_obj: Any, start_time: datetime, end_time: datetime):
        """Called after an API call completes (success or failure)."""
        # We don't need to do anything here as we handle success/failure separately
        pass

    def log_success_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: datetime, end_time: datetime):
        """Called when an API call succeeds."""
        call_id = self._get_call_id(kwargs)
        self._end_span(call_id, response_obj, kwargs)
        logger.debug(f"LiteLLM success: call_id={call_id}")

    def log_failure_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: datetime, end_time: datetime):
        """Called when an API call fails."""
        call_id = self._get_call_id(kwargs)
        exception = kwargs.get("exception", None)
        self._end_span(call_id, response_obj, kwargs, exception)
        logger.debug(f"LiteLLM failure: call_id={call_id}")

    async def async_log_pre_api_call(self, model: str, messages: List[Dict[str, Any]], kwargs: Dict[str, Any]):
        """Async version of log_pre_api_call."""
        self.log_pre_api_call(model, messages, kwargs)

    async def async_log_success_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: datetime, end_time: datetime):
        """Async version of log_success_event."""
        self.log_success_event(kwargs, response_obj, start_time, end_time)

    async def async_log_failure_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: datetime, end_time: datetime):
        """Async version of log_failure_event."""
        self.log_failure_event(kwargs, response_obj, start_time, end_time)

    def end_session(self):
        """End the session span and clean up resources."""
        # End any remaining active spans
        for call_id in list(self.active_spans.keys()):
            self._end_span(call_id)

        # End session span
        if self.session_span:
            try:
                self.session_span.end()
            except Exception as e:
                logger.warning(f"Error ending session span: {e}")
            self.session_span = None

        # Detach session token
        if self.session_token:
            try:
                detach(self.session_token)
            except Exception as e:
                logger.warning(f"Error detaching session token: {e}")
            self.session_token = None


# Register as a string callback for litellm.success_callback = ["agentops"]
def _register_litellm_callback():
    """Register the AgentOps callback with LiteLLM's callback registry."""
    try:
        import litellm
        
        # Check if agentops is already registered
        if hasattr(litellm, "_known_custom_logger_compatible_callbacks"):
            if "agentops" not in litellm._known_custom_logger_compatible_callbacks:
                litellm._known_custom_logger_compatible_callbacks["agentops"] = LiteLLMCallbackHandler
        
        logger.debug("Registered AgentOps callback with LiteLLM")
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Could not register LiteLLM callback: {e}")


# Auto-register when module is imported
_register_litellm_callback()
