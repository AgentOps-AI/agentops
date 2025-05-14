"""
LangChain callback handler for AgentOps.

This module provides the LangChain callback handler for AgentOps tracing and monitoring.
"""

from typing import Any, Dict, List, Optional, Union

from opentelemetry import trace
from opentelemetry.context import attach, detach
from opentelemetry.trace import SpanContext, set_span_in_context

from agentops.helpers.serialization import safe_serialize
from agentops.logging import logger
from agentops.sdk.core import TracingCore
from agentops.semconv import SpanKind, SpanAttributes, LangChainAttributes, LangChainAttributeValues, CoreAttributes
from agentops.integration.callbacks.langchain.utils import get_model_info

from langchain_core.callbacks.base import BaseCallbackHandler, AsyncCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.agents import AgentAction, AgentFinish


class LangchainCallbackHandler(BaseCallbackHandler):
    """
    AgentOps sync callback handler for Langchain.

    This handler creates spans for LLM calls and other langchain operations,
    maintaining proper parent-child relationships with session as root span.

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
        self.context_tokens = {}  # Store context tokens by run_id
        self.token_counts = {}  # Track token counts for streaming

        # Initialize AgentOps
        if auto_session:
            self._initialize_agentops()

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
            logger.debug("AgentOps initialized from LangChain callback handler")

        if not TracingCore.get_instance().initialized:
            logger.warning("AgentOps not initialized, session span will not be created")
            return

        tracer = TracingCore.get_instance().get_tracer()

        span_name = f"session.{SpanKind.SESSION}"

        attributes = {
            SpanAttributes.AGENTOPS_SPAN_KIND: SpanKind.SESSION,
            "session.tags": self.tags,
            "agentops.operation.name": "session",
            "span.kind": SpanKind.SESSION,
        }

        # Create a root session span
        self.session_span = tracer.start_span(span_name, attributes=attributes)

        # Attach session span to the current context
        self.session_token = attach(set_span_in_context(self.session_span))

        logger.debug("Created session span as root span for LangChain")

    def _create_span(
        self,
        operation_name: str,
        span_kind: str,
        run_id: Any = None,
        attributes: Optional[Dict[str, Any]] = None,
        parent_run_id: Optional[Any] = None,
    ):
        """
        Create a span for the operation.

        Args:
            operation_name: Name of the operation
            span_kind: Type of span
            run_id: Unique identifier for the operation
            attributes: Additional attributes for the span
            parent_run_id: The run_id of the parent span if this is a child span

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
        attributes["agentops.operation.name"] = operation_name

        if run_id is None:
            run_id = id(attributes)

        parent_span = None
        if parent_run_id is not None and parent_run_id in self.active_spans:
            # Get parent span from active spans
            parent_span = self.active_spans.get(parent_run_id)
            # Create context with parent span
            parent_ctx = set_span_in_context(parent_span)
            # Start span with parent context
            span = tracer.start_span(span_name, context=parent_ctx, attributes=attributes)
            logger.debug(f"Started span: {span_name} with parent: {parent_run_id}")
        else:
            # If no parent_run_id or parent not found, use session as parent
            parent_ctx = set_span_in_context(self.session_span)
            # Start span with session as parent context
            span = tracer.start_span(span_name, context=parent_ctx, attributes=attributes)
            logger.debug(f"Started span: {span_name} with session as parent")

        # Store span in active_spans
        self.active_spans[run_id] = span

        # Store token to detach later
        token = attach(set_span_in_context(span))
        self.context_tokens[run_id] = token

        return span

    def _end_span(self, run_id: Any):
        """
        End the span associated with the run_id.

        Args:
            run_id: Unique identifier for the operation
        """
        if run_id not in self.active_spans:
            logger.warning(f"No span found for call {run_id}")
            return

        span = self.active_spans.pop(run_id)
        token = self.context_tokens.pop(run_id, None)

        if token is not None:
            detach(token)

        try:
            span.end()
            logger.debug(f"Ended span: {span.name}")
        except Exception as e:
            logger.warning(f"Error ending span: {e}")

        # Clean up token counts if present
        if run_id in self.token_counts:
            del self.token_counts[run_id]

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Run when LLM starts running."""
        try:
            # Add null check for serialized
            if serialized is None:
                serialized = {}

            model_info = get_model_info(serialized)
            # Ensure default values if model_info returns unknown
            model_name = model_info.get("model_name", "unknown")

            attributes = {
                # Use both standard and LangChain-specific attributes
                SpanAttributes.LLM_REQUEST_MODEL: model_name,
                LangChainAttributes.LLM_MODEL: model_name,
                SpanAttributes.LLM_PROMPTS: safe_serialize(prompts),
                LangChainAttributes.LLM_NAME: serialized.get("id", "unknown_llm"),
            }

            if "kwargs" in serialized:
                for key, value in serialized["kwargs"].items():
                    if key == "temperature":
                        attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = value
                    elif key == "max_tokens":
                        attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = value
                    elif key == "top_p":
                        attributes[SpanAttributes.LLM_REQUEST_TOP_P] = value

            run_id = kwargs.get("run_id", id(serialized or {}))
            parent_run_id = kwargs.get("parent_run_id", None)

            # Initialize token count for streaming if needed
            self.token_counts[run_id] = 0

            # Log parent relationship for debugging
            if parent_run_id:
                logger.debug(f"LLM span with run_id {run_id} has parent {parent_run_id}")

            self._create_span("llm", SpanKind.LLM, run_id, attributes, parent_run_id)

            logger.debug(f"Started LLM span for {model_name}")
        except Exception as e:
            logger.warning(f"Error in on_llm_start: {e}")

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        try:
            run_id = kwargs.get("run_id", id(response))

            if run_id not in self.active_spans:
                logger.warning(f"No span found for LLM call {run_id}")
                return

            span = self.active_spans.get(run_id)

            if hasattr(response, "generations") and response.generations:
                completions = []
                for gen_list in response.generations:
                    for gen in gen_list:
                        if hasattr(gen, "text"):
                            completions.append(gen.text)

                if completions:
                    try:
                        span.set_attribute(SpanAttributes.LLM_COMPLETIONS, safe_serialize(completions))
                    except Exception as e:
                        logger.warning(f"Failed to set completions: {e}")

            if hasattr(response, "llm_output") and response.llm_output:
                token_usage = response.llm_output.get("token_usage", {})

                if "completion_tokens" in token_usage:
                    try:
                        span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, token_usage["completion_tokens"])
                    except Exception as e:
                        logger.warning(f"Failed to set completion tokens: {e}")

                if "prompt_tokens" in token_usage:
                    try:
                        span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, token_usage["prompt_tokens"])
                    except Exception as e:
                        logger.warning(f"Failed to set prompt tokens: {e}")

                if "total_tokens" in token_usage:
                    try:
                        span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, token_usage["total_tokens"])
                    except Exception as e:
                        logger.warning(f"Failed to set total tokens: {e}")

            # For streaming, record the total tokens streamed
            if run_id in self.token_counts and self.token_counts[run_id] > 0:
                try:
                    span.set_attribute(SpanAttributes.LLM_USAGE_STREAMING_TOKENS, self.token_counts[run_id])
                except Exception as e:
                    logger.warning(f"Failed to set streaming tokens: {e}")

            # End the span after setting all attributes
            self._end_span(run_id)

        except Exception as e:
            logger.warning(f"Error in on_llm_end: {e}")

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        """Run when chain starts running."""
        try:
            # Add null check for serialized
            if serialized is None:
                serialized = {}

            chain_type = serialized.get("name", "unknown_chain")

            attributes = {
                LangChainAttributes.CHAIN_TYPE: chain_type,
                LangChainAttributes.CHAIN_NAME: serialized.get("id", "unknown_chain"),
                LangChainAttributes.CHAIN_VERBOSE: serialized.get("verbose", False),
                "chain.inputs": safe_serialize(inputs),
            }

            # Add specific chain types
            if "sequential" in chain_type.lower():
                attributes[LangChainAttributes.CHAIN_KIND] = LangChainAttributeValues.CHAIN_KIND_SEQUENTIAL
            elif "llm" in chain_type.lower():
                attributes[LangChainAttributes.CHAIN_KIND] = LangChainAttributeValues.CHAIN_KIND_LLM
            elif "router" in chain_type.lower():
                attributes[LangChainAttributes.CHAIN_KIND] = LangChainAttributeValues.CHAIN_KIND_ROUTER

            run_id = kwargs.get("run_id", id(serialized or {}))
            parent_run_id = kwargs.get("parent_run_id", None)

            # Log parent relationship for debugging
            if parent_run_id:
                logger.debug(f"Chain span with run_id {run_id} has parent {parent_run_id}")

            self._create_span("chain", SpanKind.CHAIN, run_id, attributes, parent_run_id)

            logger.debug(f"Started Chain span for {chain_type}")
        except Exception as e:
            logger.warning(f"Error in on_chain_start: {e}")

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Run when chain ends running."""
        try:
            run_id = kwargs.get("run_id", id(outputs))

            if run_id not in self.active_spans:
                logger.warning(f"No span found for chain call {run_id}")
                return

            span = self.active_spans.get(run_id)

            try:
                span.set_attribute("chain.outputs", safe_serialize(outputs))
            except Exception as e:
                logger.warning(f"Failed to set chain outputs: {e}")

            # End the span after setting all attributes
            self._end_span(run_id)

        except Exception as e:
            logger.warning(f"Error in on_chain_end: {e}")

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Run when tool starts running."""
        try:
            # Add null check for serialized
            if serialized is None:
                serialized = {}

            tool_name = serialized.get("name", "unknown_tool")

            attributes = {
                LangChainAttributes.TOOL_NAME: tool_name,
                LangChainAttributes.TOOL_DESCRIPTION: serialized.get("description", ""),
                LangChainAttributes.TOOL_INPUT: input_str,
            }

            # Add more tool-specific attributes
            if "return_direct" in serialized:
                attributes[LangChainAttributes.TOOL_RETURN_DIRECT] = serialized["return_direct"]

            if "args_schema" in serialized:
                schema = serialized.get("args_schema")
                if schema:
                    schema_str = str(schema)
                    if len(schema_str) < 1000:  # Avoid extremely large attributes
                        attributes[LangChainAttributes.TOOL_ARGS_SCHEMA] = schema_str

            run_id = kwargs.get("run_id", id(serialized or {}))
            parent_run_id = kwargs.get("parent_run_id", None)

            self._create_span("tool", SpanKind.TOOL, run_id, attributes, parent_run_id)

            logger.debug(f"Started Tool span for {tool_name}")
        except Exception as e:
            logger.warning(f"Error in on_tool_start: {e}")

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Run when tool ends running."""
        try:
            run_id = kwargs.get("run_id", id(output))

            if run_id not in self.active_spans:
                logger.warning(f"No span found for tool call {run_id}")
                return

            span = self.active_spans.get(run_id)

            try:
                span.set_attribute(
                    LangChainAttributes.TOOL_OUTPUT, output if isinstance(output, str) else safe_serialize(output)
                )
            except Exception as e:
                logger.warning(f"Failed to set tool output: {e}")

            # End the span after setting all attributes
            self._end_span(run_id)

        except Exception as e:
            logger.warning(f"Error in on_tool_end: {e}")

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        """Run on agent action."""
        try:
            tool = action.tool
            tool_input = action.tool_input
            log = action.log

            attributes = {
                LangChainAttributes.AGENT_ACTION_TOOL: tool,
                LangChainAttributes.AGENT_ACTION_INPUT: safe_serialize(tool_input),
                LangChainAttributes.AGENT_ACTION_LOG: log,
            }

            run_id = kwargs.get("run_id", id(action))
            parent_run_id = kwargs.get("parent_run_id", None)

            self._create_span("agent_action", SpanKind.AGENT_ACTION, run_id, attributes, parent_run_id)

            logger.debug(f"Started Agent Action span for {tool}")
        except Exception as e:
            logger.warning(f"Error in on_agent_action: {e}")

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Run on agent end."""
        try:
            run_id = kwargs.get("run_id", id(finish))

            if run_id not in self.active_spans:
                logger.warning(f"No span found for agent finish {run_id}")
                return

            span = self.active_spans.get(run_id)

            try:
                span.set_attribute(LangChainAttributes.AGENT_FINISH_RETURN_VALUES, safe_serialize(finish.return_values))
            except Exception as e:
                logger.warning(f"Failed to set agent return values: {e}")

            try:
                span.set_attribute(LangChainAttributes.AGENT_FINISH_LOG, finish.log)
            except Exception as e:
                logger.warning(f"Failed to set agent log: {e}")

            # End the span after setting all attributes
            self._end_span(run_id)

        except Exception as e:
            logger.warning(f"Error in on_agent_finish: {e}")

    def __del__(self):
        """Clean up resources when the handler is deleted."""
        try:
            # End any remaining spans
            for run_id in list(self.active_spans.keys()):
                try:
                    self._end_span(run_id)
                except Exception as e:
                    logger.warning(f"Error ending span during cleanup: {e}")

            # End session span and detach session token
            if self.session_span:
                try:
                    # Detach session token if exists
                    if hasattr(self, "session_token") and self.session_token:
                        detach(self.session_token)

                    self.session_span.end()
                    logger.debug("Ended session span")
                except Exception as e:
                    logger.warning(f"Error ending session span: {e}")

        except Exception as e:
            logger.warning(f"Error in __del__: {e}")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run on new token from LLM."""
        try:
            run_id = kwargs.get("run_id")

            if not run_id:
                logger.warning("No run_id provided for on_llm_new_token")
                return

            if run_id not in self.active_spans:
                logger.warning(f"No span found for token in run {run_id}")
                return

            # Count tokens for later attribution
            if run_id in self.token_counts:
                self.token_counts[run_id] += 1
            else:
                self.token_counts[run_id] = 1

            # We don't set attributes on each token because it's inefficient
            # and can lead to "setting attribute on ended span" errors
            # Instead, we count tokens and set the total at the end

        except Exception as e:
            logger.warning(f"Error in on_llm_new_token: {e}")

    def on_chat_model_start(self, serialized: Dict[str, Any], messages: List[Any], **kwargs: Any) -> None:
        """Run when a chat model starts generating."""
        try:
            # Add null check for serialized
            if serialized is None:
                serialized = {}

            model_info = get_model_info(serialized)
            # Ensure default values if model_info returns unknown
            model_name = model_info.get("model_name", "unknown")

            # Extract message contents and roles
            formatted_messages = []
            roles = []

            for message in messages:
                if hasattr(message, "content") and hasattr(message, "type"):
                    formatted_messages.append({"content": message.content, "role": message.type})
                    roles.append(message.type)

            attributes = {
                # Use both standard and LangChain-specific attributes
                SpanAttributes.LLM_REQUEST_MODEL: model_name,
                LangChainAttributes.LLM_MODEL: model_name,
                SpanAttributes.LLM_PROMPTS: safe_serialize(formatted_messages),
                LangChainAttributes.LLM_NAME: serialized.get("id", "unknown_chat_model"),
                LangChainAttributes.CHAT_MESSAGE_ROLES: safe_serialize(roles),
                LangChainAttributes.CHAT_MODEL_TYPE: "chat",
            }

            # Add generation parameters
            if "kwargs" in serialized:
                for key, value in serialized["kwargs"].items():
                    if key == "temperature":
                        attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = value
                    elif key == "max_tokens":
                        attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = value
                    elif key == "top_p":
                        attributes[SpanAttributes.LLM_REQUEST_TOP_P] = value

            run_id = kwargs.get("run_id", id(serialized or {}))
            parent_run_id = kwargs.get("parent_run_id", None)

            # Initialize token count for streaming if needed
            self.token_counts[run_id] = 0

            self._create_span("chat_model", SpanKind.LLM, run_id, attributes, parent_run_id)

            logger.debug(f"Started Chat Model span for {model_name}")
        except Exception as e:
            logger.warning(f"Error in on_chat_model_start: {e}")

    def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Run when LLM errors."""
        try:
            run_id = kwargs.get("run_id")

            if not run_id or run_id not in self.active_spans:
                logger.warning(f"No span found for LLM error {run_id}")
                return

            span = self.active_spans.get(run_id)

            # Record error attributes
            try:
                span.set_attribute("error", True)
                span.set_attribute(CoreAttributes.ERROR_TYPE, error.__class__.__name__)
                span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(error))
                span.set_attribute(LangChainAttributes.LLM_ERROR, str(error))
            except Exception as e:
                logger.warning(f"Failed to set error attributes: {e}")

            # End span with error
            self._end_span(run_id)

        except Exception as e:
            logger.warning(f"Error in on_llm_error: {e}")

    def on_chain_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Run when chain errors."""
        try:
            run_id = kwargs.get("run_id")

            if not run_id or run_id not in self.active_spans:
                logger.warning(f"No span found for chain error {run_id}")
                return

            span = self.active_spans.get(run_id)

            # Record error attributes
            try:
                span.set_attribute("error", True)
                span.set_attribute(CoreAttributes.ERROR_TYPE, error.__class__.__name__)
                span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(error))
                span.set_attribute(LangChainAttributes.CHAIN_ERROR, str(error))
            except Exception as e:
                logger.warning(f"Failed to set error attributes: {e}")

            # End span with error
            self._end_span(run_id)

        except Exception as e:
            logger.warning(f"Error in on_chain_error: {e}")

    def on_tool_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Run when tool errors."""
        try:
            run_id = kwargs.get("run_id")

            if not run_id or run_id not in self.active_spans:
                logger.warning(f"No span found for tool error {run_id}")
                return

            span = self.active_spans.get(run_id)

            # Record error attributes
            try:
                span.set_attribute("error", True)
                span.set_attribute(CoreAttributes.ERROR_TYPE, error.__class__.__name__)
                span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(error))
                span.set_attribute(LangChainAttributes.TOOL_ERROR, str(error))
            except Exception as e:
                logger.warning(f"Failed to set error attributes: {e}")

            # End span with error
            self._end_span(run_id)

        except Exception as e:
            logger.warning(f"Error in on_tool_error: {e}")

    def on_text(self, text: str, **kwargs: Any) -> None:
        """
        Run on arbitrary text.

        This can be used for logging or recording intermediate steps.
        """
        try:
            run_id = kwargs.get("run_id")

            if run_id is None:
                # Create a new span for this text
                run_id = id(text)
                parent_run_id = kwargs.get("parent_run_id")

                attributes = {
                    LangChainAttributes.TEXT_CONTENT: text,
                }

                self._create_span("text", SpanKind.TEXT, run_id, attributes, parent_run_id)

                # Immediately end the span as text events are one-off
                self._end_span(run_id)
            else:
                # Try to find a parent span to add the text to
                parent_run_id = kwargs.get("parent_run_id")

                if parent_run_id and parent_run_id in self.active_spans:
                    # Add text to parent span
                    try:
                        parent_span = self.active_spans[parent_run_id]
                        # Use get_attribute to check if text already exists
                        existing_text = ""
                        try:
                            existing_text = parent_span.get_attribute(LangChainAttributes.TEXT_CONTENT) or ""
                        except Exception:
                            # If get_attribute isn't available or fails, just set the text
                            pass

                        if existing_text:
                            parent_span.set_attribute(LangChainAttributes.TEXT_CONTENT, f"{existing_text}\n{text}")
                        else:
                            parent_span.set_attribute(LangChainAttributes.TEXT_CONTENT, text)
                    except Exception as e:
                        logger.warning(f"Failed to update parent span with text: {e}")
        except Exception as e:
            logger.warning(f"Error in on_text: {e}")


class AsyncLangchainCallbackHandler(AsyncCallbackHandler):
    """
    AgentOps async callback handler for Langchain.

    This handler creates spans for LLM calls and other langchain operations,
    maintaining proper parent-child relationships with session as root span.
    This is the async version of the handler.

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
        # Create an internal sync handler to delegate to
        self._sync_handler = LangchainCallbackHandler(api_key=api_key, tags=tags, auto_session=auto_session)

    @property
    def active_spans(self):
        """Access to the active spans dictionary from sync handler."""
        return self._sync_handler.active_spans

    @property
    def session_span(self):
        """Access to the session span from sync handler."""
        return self._sync_handler.session_span

    async def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Run when LLM starts running."""
        # Delegate to sync handler
        self._sync_handler.on_llm_start(serialized, prompts, **kwargs)

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        # Delegate to sync handler
        self._sync_handler.on_llm_end(response, **kwargs)

    async def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        """Run when chain starts running."""
        # Delegate to sync handler
        self._sync_handler.on_chain_start(serialized, inputs, **kwargs)

    async def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Run when chain ends running."""
        # Delegate to sync handler
        self._sync_handler.on_chain_end(outputs, **kwargs)

    async def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Run when tool starts running."""
        # Delegate to sync handler
        self._sync_handler.on_tool_start(serialized, input_str, **kwargs)

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Run when tool ends running."""
        # Delegate to sync handler
        self._sync_handler.on_tool_end(output, **kwargs)

    async def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        """Run on agent action."""
        # Delegate to sync handler
        self._sync_handler.on_agent_action(action, **kwargs)

    async def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Run on agent end."""
        # Delegate to sync handler
        self._sync_handler.on_agent_finish(finish, **kwargs)

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run on new token from LLM."""
        # Delegate to sync handler
        self._sync_handler.on_llm_new_token(token, **kwargs)

    async def on_chat_model_start(self, serialized: Dict[str, Any], messages: List[Any], **kwargs: Any) -> None:
        """Run when a chat model starts generating."""
        # Delegate to sync handler
        self._sync_handler.on_chat_model_start(serialized, messages, **kwargs)

    async def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Run when LLM errors."""
        # Delegate to sync handler
        self._sync_handler.on_llm_error(error, **kwargs)

    async def on_chain_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Run when chain errors."""
        # Delegate to sync handler
        self._sync_handler.on_chain_error(error, **kwargs)

    async def on_tool_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Run when tool errors."""
        # Delegate to sync handler
        self._sync_handler.on_tool_error(error, **kwargs)

    async def on_text(self, text: str, **kwargs: Any) -> None:
        """Run on arbitrary text."""
        # Delegate to sync handler
        self._sync_handler.on_text(text, **kwargs)

    def __del__(self):
        """Clean up resources when the handler is deleted."""
        # The sync handler's __del__ will handle cleanup
        if hasattr(self, "_sync_handler"):
            del self._sync_handler
