"""
LiteLLM callback handler for AgentOps.

This module provides the LiteLLM callback handler for AgentOps tracing and monitoring.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import atexit

from opentelemetry import trace
from opentelemetry.context import attach, detach, get_current
from opentelemetry.trace import SpanContext, set_span_in_context, Status, StatusCode

from agentops.helpers.serialization import safe_serialize
from agentops.logging import logger
from agentops.sdk.core import TracingCore
from agentops.semconv import SpanKind, SpanAttributes
from litellm.integrations.custom_logger import CustomLogger

class LiteLLMCallbackHandler(CustomLogger):
    """
    AgentOps callback handler for LiteLLM.
    
    This handler creates spans for LLM calls, maintaining proper parent-child 
    relationships with session as root span.
    
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
        self.active_spans = {}
        self.api_key = api_key
        self.tags = tags or []
        self.session_span = None
        self.session_token = None
        self.context_tokens = {}  # Store context tokens by request_id
        
        if auto_session:
            self._initialize_agentops()
            
        atexit.register(self._cleanup)
            
    def _initialize_agentops(self):
        """Initialize AgentOps"""
        import agentops
        
        if not TracingCore.get_instance().initialized:
            init_kwargs = {
                "auto_start_session": False,
                "instrument_llm_calls": True,
            }
            
            if self.api_key:
                init_kwargs["api_key"] = self.api_key
                
            agentops.init(**init_kwargs)
            logger.debug("AgentOps initialized from LiteLLM callback handler")
            
        if not TracingCore.get_instance().initialized:
            logger.warning("AgentOps not initialized, session span will not be created")
            return
            
        tracer = TracingCore.get_instance().get_tracer()
        
        span_name = f"session.{SpanKind.SESSION}"
        
        attributes = {
            SpanAttributes.AGENTOPS_SPAN_KIND: SpanKind.SESSION,
            "session.tags": self.tags,
            SpanAttributes.OPERATION_NAME: "session",
            "span.kind": SpanKind.SESSION,
        }
        
        self.session_span = tracer.start_span(span_name, attributes=attributes)
        
        self.session_token = attach(set_span_in_context(self.session_span))
        
        logger.debug("Created session span as root span for LiteLLM")

    def _cleanup(self):
        """Clean up resources and end session span."""
        try:
            if self.session_span:
                for request_id in list(self.active_spans.keys()):
                    self._end_span(request_id)
                
                if self.session_token:
                    try:
                        detach(self.session_token)
                    except Exception as e:
                        logger.debug(f"Error detaching session context: {e}")
                
                self.session_span.end()
                logger.debug("Ended session span")
                
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

    def _create_span(
        self, 
        operation_name: str, 
        span_kind: str,
        request_id: Any = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Create a span for the operation.
        
        Args:
            operation_name: Name of the operation
            span_kind: Type of span
            request_id: Unique identifier for the request
            attributes: Additional attributes for the span
            
        Returns:
            The created span
        """
        if not TracingCore.get_instance().initialized:
            logger.warning("AgentOps not initialized, spans will not be created")
            return trace.NonRecordingSpan(SpanContext.INVALID)
            
        tracer = TracingCore.get_instance().get_tracer()
        
        span_name = f"{operation_name}.{span_kind}"
        
        if attributes is None:
            attributes = {}
            
        attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = span_kind
        attributes[SpanAttributes.OPERATION_NAME] = operation_name
        
        if request_id is None:
            request_id = id(attributes)
        
        current_context = get_current()
        
        parent_ctx = set_span_in_context(self.session_span)
        span = tracer.start_span(span_name, context=parent_ctx, attributes=attributes)
        
        self.active_spans[request_id] = span
        
        token = attach(set_span_in_context(span))
        self.context_tokens[request_id] = token
        
        return span

    def _end_span(self, request_id: Any):
        """
        End the span associated with the request_id.
        
        Args:
            request_id: Unique identifier for the request
        """
        if request_id not in self.active_spans:
            logger.warning(f"No span found for request {request_id}")
            return
            
        span = self.active_spans.pop(request_id)
        token = self.context_tokens.pop(request_id, None)
        
        if token is not None:
            try:
                detach(token)
            except Exception as e:
                logger.debug(f"Error detaching context: {e}")
            
        try:
            span.end()
            logger.debug(f"Ended span: {span.name}")
        except Exception as e:
            logger.warning(f"Error ending span: {e}")

    def _format_messages(self, messages: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
        """
        Format messages for span attributes.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Formatted list of messages
        """
        if not messages:
            return []
            
        formatted_messages = []
        for message in messages:
            if isinstance(message, dict) and "role" in message and "content" in message:
                formatted_messages.append({
                    "role": message["role"],
                    "content": message["content"]
                })
            else:
                logger.warning(f"Invalid message format: {message}")
                
        return formatted_messages

    def _safe_set_attribute(self, span: Any, key: str, value: Any):
        """
        Safely set a span attribute, handling None values and invalid types.
        
        Args:
            span: The span to set the attribute on
            key: The attribute key
            value: The attribute value
        """
        if value is not None:
            try:
                span.set_attribute(key, value)
            except Exception as e:
                logger.debug(f"Error setting attribute {key}: {e}")

    def log_pre_api_call(self, model: str, messages: List[Dict[str, str]], kwargs: Dict[str, Any]):
        """Handle pre-API call event."""
        try:
            request_id = id(kwargs)
            
            provider = kwargs.get("provider", "openai")
            model_name = model
            
            formatted_messages = self._format_messages(messages)
            
            attributes = {
                SpanAttributes.LLM_REQUEST_PROVIDER: provider,
                SpanAttributes.LLM_REQUEST_MODEL: model_name,
                SpanAttributes.LLM_REQUEST_TYPE: "completion",
                SpanAttributes.LLM_PROMPTS: safe_serialize(formatted_messages),
            }
            
            if "temperature" in kwargs:
                attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = float(kwargs["temperature"])
            if "max_tokens" in kwargs:
                attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = int(kwargs["max_tokens"])
            if "async" in kwargs:
                attributes[SpanAttributes.LLM_REQUEST_STREAMING] = bool(kwargs["async"])
            
            if "litellm_params" in kwargs and "metadata" in kwargs["litellm_params"]:
                for key, value in kwargs["litellm_params"]["metadata"].items():
                    attributes[f"llm.metadata.{key}"] = str(value)
            
            span = self._create_span(
                operation_name="litellm.completion",
                span_kind=SpanKind.LLM_CALL,
                request_id=request_id,
                attributes=attributes
            )
            
            logger.debug(f"Created span for {'async' if kwargs.get('async') else 'sync'} LLM request: {model_name}")
            
        except Exception as e:
            logger.warning(f"Error in log_pre_api_call: {e}")

    def log_success_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: datetime, end_time: datetime):
        """Handle successful API call event."""
        try:
            request_id = id(kwargs)
            span = self.active_spans.get(request_id)
            
            if not span:
                logger.warning(f"No span found for successful request {request_id}")
                return
                
            if hasattr(response_obj, "usage"):
                self._safe_set_attribute(span, SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, response_obj.usage.completion_tokens)
                self._safe_set_attribute(span, SpanAttributes.LLM_USAGE_PROMPT_TOKENS, response_obj.usage.prompt_tokens)
                self._safe_set_attribute(span, SpanAttributes.LLM_USAGE_TOTAL_TOKENS, response_obj.usage.total_tokens)
            
            if hasattr(response_obj, "choices") and len(response_obj.choices) > 0:
                message = response_obj.choices[0].message
                if message.content:
                    self._safe_set_attribute(span, SpanAttributes.AGENTOPS_ENTITY_OUTPUT, str(message.content))
                    self._safe_set_attribute(span, SpanAttributes.LLM_COMPLETIONS, safe_serialize(message))
            
            duration = (end_time - start_time).total_seconds()
            self._safe_set_attribute(span, "llm.duration", float(duration))
            
            if "complete_streaming_response" in kwargs:
                self._safe_set_attribute(span, SpanAttributes.AGENTOPS_ENTITY_OUTPUT, str(kwargs["complete_streaming_response"]))
                
            if "response_cost" in kwargs:
                self._safe_set_attribute(span, "llm.cost", float(kwargs["response_cost"]))
                
            if "cache_hit" in kwargs and kwargs["cache_hit"] is not None:
                self._safe_set_attribute(span, "llm.cache_hit", bool(kwargs["cache_hit"]))
                
            span.set_status(Status(StatusCode.OK))
            self._end_span(request_id)
            
            logger.debug(f"Completed span for {'async' if kwargs.get('async') else 'sync'} LLM request: {request_id}")
            
        except Exception as e:
            logger.warning(f"Error in log_success_event: {e}")

    def log_failure_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: datetime, end_time: datetime):
        """Handle failed API call event."""
        try:
            request_id = id(kwargs)
            span = self.active_spans.get(request_id)
            
            if not span:
                logger.warning(f"No span found for failed request {request_id}")
                return
                
            self._safe_set_attribute(span, "llm.error", str(response_obj))
            if "exception" in kwargs:
                self._safe_set_attribute(span, "llm.error_type", str(type(kwargs["exception"]).__name__))
            if "traceback_exception" in kwargs:
                self._safe_set_attribute(span, "llm.error_traceback", str(kwargs["traceback_exception"]))
                
            duration = (end_time - start_time).total_seconds()
            self._safe_set_attribute(span, "llm.duration", float(duration))
            
            span.set_status(Status(StatusCode.ERROR))
            self._end_span(request_id)
            
            logger.debug(f"Completed span for failed {'async' if kwargs.get('async') else 'sync'} LLM request: {request_id}")
            
        except Exception as e:
            logger.warning(f"Error in log_failure_event: {e}")

    async def async_log_pre_api_call(self, model: str, messages: List[Dict[str, str]], kwargs: Dict[str, Any]):
        """Handle pre-API call event asynchronously."""
        try:
            request_id = id(kwargs)
            
            provider = kwargs.get("provider", "openai")
            model_name = model
            
            formatted_messages = self._format_messages(messages)
            
            attributes = {
                SpanAttributes.LLM_REQUEST_PROVIDER: provider,
                SpanAttributes.LLM_REQUEST_MODEL: model_name,
                SpanAttributes.LLM_REQUEST_TYPE: "completion",
                SpanAttributes.LLM_PROMPTS: safe_serialize(formatted_messages),
            }
            
            if "temperature" in kwargs:
                attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = float(kwargs["temperature"])
            if "max_tokens" in kwargs:
                attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = int(kwargs["max_tokens"])
            attributes[SpanAttributes.LLM_REQUEST_STREAMING] = True
            
            if "litellm_params" in kwargs and "metadata" in kwargs["litellm_params"]:
                for key, value in kwargs["litellm_params"]["metadata"].items():
                    attributes[f"llm.metadata.{key}"] = str(value)
            
            span = self._create_span(
                operation_name="litellm.completion",
                span_kind=SpanKind.LLM_CALL,
                request_id=request_id,
                attributes=attributes
            )
            
            logger.debug(f"Created span for async LLM request: {model_name}")
            
        except Exception as e:
            logger.warning(f"Error in async_log_pre_api_call: {e}")

    async def async_log_success_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: datetime, end_time: datetime):
        """Handle successful API call event asynchronously."""
        try:
            request_id = id(kwargs)
            span = self.active_spans.get(request_id)
            
            if not span:
                logger.warning(f"No span found for successful async request {request_id}")
                return
                
            if hasattr(response_obj, "usage"):
                self._safe_set_attribute(span, SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, response_obj.usage.completion_tokens)
                self._safe_set_attribute(span, SpanAttributes.LLM_USAGE_PROMPT_TOKENS, response_obj.usage.prompt_tokens)
                self._safe_set_attribute(span, SpanAttributes.LLM_USAGE_TOTAL_TOKENS, response_obj.usage.total_tokens)
            
            if hasattr(response_obj, "choices") and len(response_obj.choices) > 0:
                message = response_obj.choices[0].message
                if message.content:
                    self._safe_set_attribute(span, SpanAttributes.AGENTOPS_ENTITY_OUTPUT, str(message.content))
                    self._safe_set_attribute(span, SpanAttributes.LLM_COMPLETIONS, safe_serialize(message))
            
            duration = (end_time - start_time).total_seconds()
            self._safe_set_attribute(span, "llm.duration", float(duration))
            
            if "complete_streaming_response" in kwargs:
                self._safe_set_attribute(span, SpanAttributes.AGENTOPS_ENTITY_OUTPUT, str(kwargs["complete_streaming_response"]))
                
            if "response_cost" in kwargs:
                self._safe_set_attribute(span, "llm.cost", float(kwargs["response_cost"]))
                
            if "cache_hit" in kwargs and kwargs["cache_hit"] is not None:
                self._safe_set_attribute(span, "llm.cache_hit", bool(kwargs["cache_hit"]))
                
            span.set_status(Status(StatusCode.OK))
            self._end_span(request_id)
            
            logger.debug(f"Completed span for async LLM request: {request_id}")
            
        except Exception as e:
            logger.warning(f"Error in async_log_success_event: {e}")

    async def async_log_failure_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: datetime, end_time: datetime):
        """Handle failed API call event asynchronously."""
        try:
            request_id = id(kwargs)
            span = self.active_spans.get(request_id)
            
            if not span:
                logger.warning(f"No span found for failed async request {request_id}")
                return
                
            self._safe_set_attribute(span, "llm.error", str(response_obj))
            if "exception" in kwargs:
                self._safe_set_attribute(span, "llm.error_type", str(type(kwargs["exception"]).__name__))
            if "traceback_exception" in kwargs:
                self._safe_set_attribute(span, "llm.error_traceback", str(kwargs["traceback_exception"]))
                
            duration = (end_time - start_time).total_seconds()
            self._safe_set_attribute(span, "llm.duration", float(duration))
            
            span.set_status(Status(StatusCode.ERROR))
            self._end_span(request_id)
            
            logger.debug(f"Completed span for failed async LLM request: {request_id}")
            
        except Exception as e:
            logger.warning(f"Error in async_log_failure_event: {e}")

    async def async_log_post_api_call(self, kwargs: Dict[str, Any], response_obj: Any, start_time: datetime, end_time: datetime):
        """Handle post-API call event asynchronously."""
        # This is called right after the API call is made
        # We don't need to do anything here as we handle everything in success/failure events
        pass