"""Langchain callback handler using OpenTelemetry.

This module provides callback handlers for Langchain that integrate with OpenTelemetry
for tracing and monitoring. It supports both synchronous and asynchronous operations,
tracking various events in the Langchain execution flow including LLM calls, tool usage,
chain execution, and agent actions.
"""

from typing import Dict, Any, List, Optional, Sequence, Union
from uuid import UUID
import logging
import os
from collections import defaultdict

from tenacity import RetryCallState
from langchain_core.agents import AgentFinish, AgentAction
from langchain_core.documents import Document
from langchain_core.outputs import ChatGenerationChunk, GenerationChunk, LLMResult, Generation
from langchain_core.callbacks.base import BaseCallbackHandler, AsyncCallbackHandler
from langchain_core.messages import BaseMessage, AIMessage, AIMessageChunk
from opentelemetry.trace import Status, StatusCode

from agentops.sdk.decorators.utility import _create_as_current_span
from agentops.semconv import SpanKind
from agentops.semconv.langchain_attributes import LangchainAttributes
from agentops.logging import logger

def get_model_from_kwargs(kwargs: Any) -> str:
    """Extract model name from kwargs.
    
    This function attempts to get the model name from the invocation parameters
    in the kwargs dictionary. It checks for both 'model' and '_type' keys in the
    invocation_params dictionary.
    
    Args:
        kwargs: Dictionary containing invocation parameters
        
    Returns:
        str: The model name if found, otherwise 'unknown_model'
    """
    if "model" in kwargs.get("invocation_params", {}):
        return kwargs["invocation_params"]["model"]
    elif "_type" in kwargs.get("invocation_params", {}):
        return kwargs["invocation_params"]["_type"]
    return "unknown_model"

def _create_span_attributes(
    run_id: UUID,
    parent_run_id: Optional[UUID] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create common span attributes.
    
    This function creates a standardized set of attributes for OpenTelemetry spans.
    It includes common attributes like run_id, parent_run_id, tags, and metadata,
    along with any additional attributes passed in kwargs.
    
    Args:
        run_id: Unique identifier for the current run
        parent_run_id: Optional identifier for the parent run
        tags: Optional list of tags for the span
        metadata: Optional dictionary of metadata
        **kwargs: Additional attributes to include
        
    Returns:
        Dict[str, Any]: Dictionary of span attributes
    """
    return {
        LangchainAttributes.RUN_ID: str(run_id),
        LangchainAttributes.PARENT_RUN_ID: str(parent_run_id) if parent_run_id else "",
        LangchainAttributes.TAGS: str(tags or []),
        LangchainAttributes.METADATA: str(metadata or {}),
        **kwargs,
    }

def _handle_span_error(span: Any, error: Exception, **kwargs: Any) -> None:
    """Handle span error consistently.
    
    This function provides a standardized way to handle errors in spans,
    setting appropriate error attributes and status codes.
    
    Args:
        span: The OpenTelemetry span to update
        error: The exception that occurred
        **kwargs: Additional context for the error
    """
    span.set_status(Status(StatusCode.ERROR))
    span.set_attribute(LangchainAttributes.ERROR_TYPE, type(error).__name__)
    span.set_attribute(LangchainAttributes.ERROR_MESSAGE, str(error))
    span.set_attribute(LangchainAttributes.ERROR_DETAILS, {
        "run_id": kwargs.get("run_id"),
        "parent_run_id": kwargs.get("parent_run_id"),
        "kwargs": str(kwargs)
    })
    span.end()

class BaseLangchainHandler:
    """Base class for Langchain handlers with common functionality.
    
    This class provides shared functionality for both synchronous and asynchronous
    Langchain callback handlers, including initialization, span tracking, and
    common utility methods.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        max_wait_time: Optional[int] = None,
        max_queue_size: Optional[int] = None,
        default_tags: List[str] = None,
    ):
        """Initialize the handler with configuration options.
        
        Args:
            api_key: Optional API key for AgentOps
            endpoint: Optional endpoint URL for AgentOps
            max_wait_time: Optional maximum wait time for operations
            max_queue_size: Optional maximum size of the operation queue
            default_tags: Optional list of default tags for spans
        """
        # Set up logging
        logging_level = os.getenv("AGENTOPS_LOGGING_LEVEL")
        log_levels = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "DEBUG": logging.DEBUG,
        }
        logger.setLevel(log_levels.get(logging_level or "INFO", "INFO"))

        # Initialize AgentOps client
        from agentops import Client
        self.client = Client()
        self.client.configure(
            api_key=api_key or "test-api-key",
            endpoint=endpoint,
            max_wait_time=max_wait_time,
            max_queue_size=max_queue_size,
            default_tags=default_tags or ["langchain", "sync" if isinstance(self, LangchainCallbackHandler) else "async"],
        )
        self.client.init()

        # Initialize span tracking
        self._llm_spans: Dict[str, Any] = {}
        self._tool_spans: Dict[str, Any] = {}
        self._chain_spans: Dict[str, Any] = {}
        self._retriever_spans: Dict[str, Any] = {}
        self._agent_actions: Dict[UUID, List[Any]] = defaultdict(list)

    def _handle_llm_response(self, span: Any, response: LLMResult) -> None:
        """Handle LLM response and set appropriate attributes.
        
        This method processes an LLM response and updates the span with relevant
        information including the response text, token usage, and other metadata.
        
        Args:
            span: The OpenTelemetry span to update
            response: The LLM response to process
        """
        if not hasattr(response, "generations"):
            return

        for generation_list in response.generations:
            for generation in generation_list:
                if isinstance(generation, Generation):
                    if generation.text:
                        span.set_attribute(LangchainAttributes.RESPONSE, generation.text)
                elif hasattr(generation, "message"):
                    if isinstance(generation.message, AIMessage) and generation.message.content:
                        span.set_attribute(LangchainAttributes.RESPONSE, generation.message.content)
                    elif isinstance(generation.message, AIMessageChunk) and generation.message.content:
                        current_completion = span.get_attribute(LangchainAttributes.RESPONSE) or ""
                        span.set_attribute(LangchainAttributes.RESPONSE, current_completion + generation.message.content)

        # Handle token usage
        if hasattr(response, "llm_output") and isinstance(response.llm_output, dict):
            token_usage = response.llm_output.get("token_usage", {})
            if isinstance(token_usage, dict):
                span.set_attribute(LangchainAttributes.PROMPT_TOKENS, token_usage.get("prompt_tokens", 0))
                span.set_attribute(LangchainAttributes.COMPLETION_TOKENS, token_usage.get("completion_tokens", 0))
                span.set_attribute(LangchainAttributes.TOTAL_TOKENS, token_usage.get("total_tokens", 0))

    def _handle_agent_finish(self, run_id: UUID, finish: AgentFinish) -> None:
        """Handle agent finish event and update spans.
        
        This method processes the completion of an agent's task, updating the
        relevant spans with final outputs and status.
        
        Args:
            run_id: Unique identifier for the agent run
            finish: The AgentFinish event containing final outputs
        """
        agent_spans = self._agent_actions.get(run_id, [])
        if not agent_spans:
            return

        last_span = agent_spans[-1]
        last_span.set_attribute(LangchainAttributes.OUTPUTS, str(finish.return_values))
        last_span.set_attribute(LangchainAttributes.TOOL_LOG, finish.log)
        last_span.set_status(Status(StatusCode.OK))
        last_span.end()

        # Record all agent actions
        for span in agent_spans[:-1]:
            span.set_status(Status(StatusCode.OK))
            span.end()

        self._agent_actions.pop(run_id, None)

    @property
    def current_session_ids(self) -> List[str]:
        """Get current session IDs.
        
        Returns:
            List[str]: List of current session IDs from the AgentOps client
        """
        return self.client.current_session_ids

class LangchainCallbackHandler(BaseLangchainHandler, BaseCallbackHandler):
    """Callback handler for Langchain using OpenTelemetry.
    
    This class implements the synchronous callback interface for Langchain,
    tracking various events in the execution flow and creating appropriate
    OpenTelemetry spans for monitoring and debugging.
    """

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        """Handle LLM start event.
        
        This method is called when an LLM operation begins. It creates a new span
        to track the operation and stores relevant information about the model and
        input prompts.
        
        Args:
            serialized: Serialized information about the LLM
            prompts: List of input prompts
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            with _create_as_current_span(
                name="llm",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    model=get_model_from_kwargs(kwargs),
                    prompt=prompts[0] if prompts else "",
                    **kwargs,
                ),
            ) as span:
                self._llm_spans[run_id] = span

        except Exception as e:
            logger.error(f"Error in on_llm_start: {str(e)}")

    def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any,
    ) -> None:
        """Handle LLM end event.
        
        This method is called when an LLM operation completes. It processes the
        response, updates the span with results, and handles any errors that
        occurred during the operation.
        
        Args:
            response: The LLM result containing generations and metadata
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        span = self._llm_spans.get(run_id)
        if not span:
            return

        try:
            self._handle_llm_response(span, response)
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            logger.error(f"Error in on_llm_end: {str(e)}")
            _handle_span_error(span, e, **kwargs)
        finally:
            span.end()
            self._llm_spans.pop(run_id, None)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle LLM error event.
        
        This method is called when an error occurs during an LLM operation.
        It updates the span with error information and marks it as failed.
        
        Args:
            error: The exception that occurred
            run_id: Unique identifier for the LLM run
            **kwargs: Additional error context
        """
        if str(run_id) in self._llm_spans:
            span = self._llm_spans[str(run_id)]
            _handle_span_error(span, error, run_id=run_id, **kwargs)

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        **kwargs: Any,
    ) -> None:
        """Handle chat model start event.
        
        This method is called when a chat model operation begins. It creates a
        new span to track the operation and stores information about the model
        and input messages.
        
        Args:
            serialized: Serialized information about the chat model
            messages: List of message lists containing the conversation
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            parsed_messages = [
                {"role": message.type, "content": message.content}
                for message in messages[0]
                if message.type in ["system", "human"]
            ]

            with _create_as_current_span(
                name="chat_model",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    model=get_model_from_kwargs(kwargs),
                    messages=str(parsed_messages),
                    **kwargs,
                ),
            ) as span:
                self._llm_spans[run_id] = span

        except Exception as e:
            logger.error(f"Error in on_chat_model_start: {str(e)}")

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Handle chain start event.
        
        This method is called when a Langchain chain operation begins. It creates
        a new span to track the chain execution and stores information about the
        chain and its inputs.
        
        Args:
            serialized: Serialized information about the chain
            inputs: Dictionary of input values for the chain
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            with _create_as_current_span(
                name="chain",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    chain_name=serialized.get("name", "unknown"),
                    inputs=str(inputs or {}),
                    **kwargs,
                ),
            ) as span:
                self._chain_spans[run_id] = span

        except Exception as e:
            logger.error(f"Error in on_chain_start: {str(e)}")

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle chain end event.
        
        This method is called when a Langchain chain operation completes. It
        updates the span with the chain's outputs and marks it as successful.
        
        Args:
            outputs: Dictionary of output values from the chain
            run_id: Unique identifier for the chain run
            **kwargs: Additional arguments
        """
        if str(run_id) in self._chain_spans:
            span = self._chain_spans[str(run_id)]
            span.set_attribute(LangchainAttributes.CHAIN_OUTPUTS, str(outputs))
            span.end()

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle chain error event.
        
        This method is called when an error occurs during a chain operation.
        It updates the span with error information and marks it as failed.
        
        Args:
            error: The exception that occurred
            run_id: Unique identifier for the chain run
            **kwargs: Additional error context
        """
        if str(run_id) in self._chain_spans:
            span = self._chain_spans[str(run_id)]
            _handle_span_error(span, error, run_id=run_id, **kwargs)

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Handle tool start event.
        
        This method is called when a tool operation begins. It creates a new span
        to track the tool execution and stores information about the tool and its
        inputs.
        
        Args:
            serialized: Serialized information about the tool
            input_str: String input for the tool
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            with _create_as_current_span(
                name="tool",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    tool_name=serialized.get("name", "unknown"),
                    tool_input=input_str,
                    inputs=str(kwargs.get("inputs", {})),
                    **kwargs,
                ),
            ) as span:
                self._tool_spans[run_id] = span

        except Exception as e:
            logger.error(f"Error in on_tool_start: {str(e)}")

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle tool end event.
        
        This method is called when a tool operation completes. It updates the span
        with the tool's output and handles any errors that occurred during the
        operation.
        
        Args:
            output: String output from the tool
            run_id: Unique identifier for the tool run
            **kwargs: Additional arguments
        """
        if str(run_id) in self._tool_spans:
            span = self._tool_spans[str(run_id)]
            span.set_attribute(LangchainAttributes.TOOL_OUTPUT, output)
            
            if kwargs.get("name") == "_Exception":
                _handle_span_error(span, Exception(output), run_id=run_id, **kwargs)
            else:
                span.end()

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle tool error event.
        
        This method is called when an error occurs during a tool operation.
        It updates the span with error information and marks it as failed.
        
        Args:
            error: The exception that occurred
            run_id: Unique identifier for the tool run
            **kwargs: Additional error context
        """
        if str(run_id) in self._tool_spans:
            span = self._tool_spans[str(run_id)]
            _handle_span_error(span, error, run_id=run_id, **kwargs)

    def on_retriever_start(
        self,
        serialized: Dict[str, Any],
        query: str,
        **kwargs: Any,
    ) -> None:
        """Handle retriever start event.
        
        This method is called when a retriever operation begins. It creates a new
        span to track the retrieval process and stores information about the
        retriever and the query.
        
        Args:
            serialized: Serialized information about the retriever
            query: The search query string
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            with _create_as_current_span(
                name="retriever",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    retriever_name=serialized.get("name", "unknown"),
                    query=query,
                    **kwargs,
                ),
            ) as span:
                self._retriever_spans[run_id] = span

        except Exception as e:
            logger.error(f"Error in on_retriever_start: {str(e)}")

    def on_retriever_end(
        self,
        documents: Sequence[Document],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle retriever end event.
        
        This method is called when a retriever operation completes. It updates
        the span with the retrieved documents and marks it as successful.
        
        Args:
            documents: Sequence of retrieved documents
            run_id: Unique identifier for the retriever run
            **kwargs: Additional arguments
        """
        if str(run_id) in self._retriever_spans:
            span = self._retriever_spans[str(run_id)]
            span.set_attribute(LangchainAttributes.RETRIEVER_DOCUMENTS, str(documents))
            span.end()

    def on_retriever_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle retriever error event.
        
        This method is called when an error occurs during a retriever operation.
        It updates the span with error information and marks it as failed.
        
        Args:
            error: The exception that occurred
            run_id: Unique identifier for the retriever run
            **kwargs: Additional error context
        """
        if str(run_id) in self._retriever_spans:
            span = self._retriever_spans[str(run_id)]
            _handle_span_error(span, error, run_id=run_id, **kwargs)

    def on_agent_action(
        self,
        action: AgentAction,
        **kwargs: Any,
    ) -> None:
        """Handle agent action event.
        
        This method is called when an agent performs an action. It creates a new
        span to track the action and stores information about the tool being used
        and its inputs.
        
        Args:
            action: The agent action containing tool and input information
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            with _create_as_current_span(
                name="agent_action",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    agent_name=action.tool,
                    tool_input=action.tool_input,
                    tool_log=action.log,
                    **kwargs,
                ),
            ) as span:
                self._agent_actions[run_id].append(span)

        except Exception as e:
            logger.error(f"Error in on_agent_action: {str(e)}")

    def on_agent_finish(
        self,
        finish: AgentFinish,
        **kwargs: Any,
    ) -> None:
        """Handle agent finish event.
        
        This method is called when an agent completes its task. It updates all
        relevant spans with final outputs and marks them as successful.
        
        Args:
            finish: The AgentFinish event containing final outputs
            **kwargs: Additional arguments including run_id
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            self._handle_agent_finish(run_id, finish)
        except Exception as e:
            logger.error(f"Error in on_agent_finish: {str(e)}")

    def on_retry(
        self,
        retry_state: RetryCallState,
        **kwargs: Any,
    ) -> None:
        """Handle retry event.
        
        This method is called when an operation is being retried. It creates a
        new span to track the retry attempt and stores information about the
        error that caused the retry.
        
        Args:
            retry_state: State information about the retry attempt
            **kwargs: Additional arguments including run_id
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            with _create_as_current_span(
                name="retry",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    retry_attempt=retry_state.attempt_number,
                    error_type=type(retry_state.outcome.exception()).__name__,
                    error_message=str(retry_state.outcome.exception()),
                    **kwargs,
                ),
            ) as span:
                span.set_status(Status(StatusCode.ERROR))
                span.end()

        except Exception as e:
            logger.error(f"Error in on_retry: {str(e)}")

    def on_llm_new_token(
        self,
        token: str,
        **kwargs: Any,
    ) -> None:
        """Handle new LLM token event.
        
        This method is called when a new token is generated during streaming
        LLM responses. It updates the span with the accumulated response text.
        
        Args:
            token: The new token generated
            **kwargs: Additional arguments including run_id
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        span = self._llm_spans.get(run_id)
        if not span:
            return

        try:
            current_completion = span.get_attribute(LangchainAttributes.RESPONSE) or ""
            span.set_attribute(LangchainAttributes.RESPONSE, current_completion + token)
        except Exception as e:
            logger.error(f"Error in on_llm_new_token: {str(e)}")


class AsyncLangchainCallbackHandler(BaseLangchainHandler, AsyncCallbackHandler):
    """Async callback handler for Langchain using OpenTelemetry.
    
    This class implements the asynchronous callback interface for Langchain,
    providing the same functionality as the synchronous handler but with
    async/await support for better performance in asynchronous environments.
    """

    async def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        """Handle LLM start event asynchronously.
        
        This method is called when an LLM operation begins. It creates a new span
        to track the operation and stores relevant information about the model and
        input prompts.
        
        Args:
            serialized: Serialized information about the LLM
            prompts: List of input prompts
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            with _create_as_current_span(
                name="llm",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    model=get_model_from_kwargs(kwargs),
                    prompt=prompts[0] if prompts else "",
                    **kwargs,
                ),
            ) as span:
                self._llm_spans[run_id] = span

        except Exception as e:
            logger.error(f"Error in on_llm_start: {str(e)}")

    async def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any,
    ) -> None:
        """Handle LLM end event asynchronously.
        
        This method is called when an LLM operation completes. It processes the
        response, updates the span with results, and handles any errors that
        occurred during the operation.
        
        Args:
            response: The LLM result containing generations and metadata
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        span = self._llm_spans.get(run_id)
        if not span:
            return

        try:
            self._handle_llm_response(span, response)
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            logger.error(f"Error in on_llm_end: {str(e)}")
            _handle_span_error(span, e, **kwargs)
        finally:
            span.end()
            self._llm_spans.pop(run_id, None)

    async def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle LLM error event asynchronously.
        
        This method is called when an error occurs during an LLM operation.
        It updates the span with error information and marks it as failed.
        
        Args:
            error: The exception that occurred
            run_id: Unique identifier for the LLM run
            **kwargs: Additional error context
        """
        if str(run_id) in self._llm_spans:
            span = self._llm_spans[str(run_id)]
            _handle_span_error(span, error, run_id=run_id, **kwargs)

    async def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        **kwargs: Any,
    ) -> None:
        """Handle chat model start event asynchronously.
        
        This method is called when a chat model operation begins. It creates a
        new span to track the operation and stores information about the model
        and input messages.
        
        Args:
            serialized: Serialized information about the chat model
            messages: List of message lists containing the conversation
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            parsed_messages = [
                {"role": message.type, "content": message.content}
                for message in messages[0]
                if message.type in ["system", "human"]
            ]

            with _create_as_current_span(
                name="chat_model",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    model=get_model_from_kwargs(kwargs),
                    messages=str(parsed_messages),
                    **kwargs,
                ),
            ) as span:
                self._llm_spans[run_id] = span

        except Exception as e:
            logger.error(f"Error in on_chat_model_start: {str(e)}")

    async def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Handle chain start event asynchronously.
        
        This method is called when a Langchain chain operation begins. It creates
        a new span to track the chain execution and stores information about the
        chain and its inputs.
        
        Args:
            serialized: Serialized information about the chain
            inputs: Dictionary of input values for the chain
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            with _create_as_current_span(
                name="chain",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    chain_name=serialized.get("name", "unknown"),
                    inputs=str(inputs or {}),
                    **kwargs,
                ),
            ) as span:
                self._chain_spans[run_id] = span

        except Exception as e:
            logger.error(f"Error in on_chain_start: {str(e)}")

    async def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle chain end event asynchronously.
        
        This method is called when a Langchain chain operation completes. It
        updates the span with the chain's outputs and marks it as successful.
        
        Args:
            outputs: Dictionary of output values from the chain
            run_id: Unique identifier for the chain run
            **kwargs: Additional arguments
        """
        if str(run_id) in self._chain_spans:
            span = self._chain_spans[str(run_id)]
            span.set_attribute(LangchainAttributes.CHAIN_OUTPUTS, str(outputs))
            span.end()

    async def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle chain error event asynchronously.
        
        This method is called when an error occurs during a chain operation.
        It updates the span with error information and marks it as failed.
        
        Args:
            error: The exception that occurred
            run_id: Unique identifier for the chain run
            **kwargs: Additional error context
        """
        if str(run_id) in self._chain_spans:
            span = self._chain_spans[str(run_id)]
            _handle_span_error(span, error, run_id=run_id, **kwargs)

    async def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Handle tool start event asynchronously.
        
        This method is called when a tool operation begins. It creates a new span
        to track the tool execution and stores information about the tool and its
        inputs.
        
        Args:
            serialized: Serialized information about the tool
            input_str: String input for the tool
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            with _create_as_current_span(
                name="tool",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    tool_name=serialized.get("name", "unknown"),
                    tool_input=input_str,
                    inputs=str(kwargs.get("inputs", {})),
                    **kwargs,
                ),
            ) as span:
                self._tool_spans[run_id] = span

        except Exception as e:
            logger.error(f"Error in on_tool_start: {str(e)}")

    async def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle tool end event asynchronously.
        
        This method is called when a tool operation completes. It updates the span
        with the tool's output and handles any errors that occurred during the
        operation.
        
        Args:
            output: String output from the tool
            run_id: Unique identifier for the tool run
            **kwargs: Additional arguments
        """
        if str(run_id) in self._tool_spans:
            span = self._tool_spans[str(run_id)]
            span.set_attribute(LangchainAttributes.TOOL_OUTPUT, output)
            
            if kwargs.get("name") == "_Exception":
                _handle_span_error(span, Exception(output), run_id=run_id, **kwargs)
            else:
                span.end()

    async def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle tool error event asynchronously.
        
        This method is called when an error occurs during a tool operation.
        It updates the span with error information and marks it as failed.
        
        Args:
            error: The exception that occurred
            run_id: Unique identifier for the tool run
            **kwargs: Additional error context
        """
        if str(run_id) in self._tool_spans:
            span = self._tool_spans[str(run_id)]
            _handle_span_error(span, error, run_id=run_id, **kwargs)

    async def on_retriever_start(
        self,
        serialized: Dict[str, Any],
        query: str,
        **kwargs: Any,
    ) -> None:
        """Handle retriever start event asynchronously.
        
        This method is called when a retriever operation begins. It creates a new
        span to track the retrieval process and stores information about the
        retriever and the query.
        
        Args:
            serialized: Serialized information about the retriever
            query: The search query string
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            with _create_as_current_span(
                name="retriever",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    retriever_name=serialized.get("name", "unknown"),
                    query=query,
                    **kwargs,
                ),
            ) as span:
                self._retriever_spans[run_id] = span

        except Exception as e:
            logger.error(f"Error in on_retriever_start: {str(e)}")

    async def on_retriever_end(
        self,
        documents: Sequence[Document],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle retriever end event asynchronously.
        
        This method is called when a retriever operation completes. It updates
        the span with the retrieved documents and marks it as successful.
        
        Args:
            documents: Sequence of retrieved documents
            run_id: Unique identifier for the retriever run
            **kwargs: Additional arguments
        """
        if str(run_id) in self._retriever_spans:
            span = self._retriever_spans[str(run_id)]
            span.set_attribute(LangchainAttributes.RETRIEVER_DOCUMENTS, str(documents))
            span.end()

    async def on_retriever_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle retriever error event asynchronously.
        
        This method is called when an error occurs during a retriever operation.
        It updates the span with error information and marks it as failed.
        
        Args:
            error: The exception that occurred
            run_id: Unique identifier for the retriever run
            **kwargs: Additional error context
        """
        if str(run_id) in self._retriever_spans:
            span = self._retriever_spans[str(run_id)]
            _handle_span_error(span, error, run_id=run_id, **kwargs)

    async def on_agent_action(
        self,
        action: AgentAction,
        **kwargs: Any,
    ) -> None:
        """Handle agent action event asynchronously.
        
        This method is called when an agent performs an action. It creates a new
        span to track the action and stores information about the tool being used
        and its inputs.
        
        Args:
            action: The agent action containing tool and input information
            **kwargs: Additional arguments including run_id and metadata
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            with _create_as_current_span(
                name="agent_action",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    agent_name=action.tool,
                    tool_input=action.tool_input,
                    tool_log=action.log,
                    **kwargs,
                ),
            ) as span:
                self._agent_actions[run_id].append(span)

        except Exception as e:
            logger.error(f"Error in on_agent_action: {str(e)}")

    async def on_agent_finish(
        self,
        finish: AgentFinish,
        **kwargs: Any,
    ) -> None:
        """Handle agent finish event asynchronously.
        
        This method is called when an agent completes its task. It updates all
        relevant spans with final outputs and marks them as successful.
        
        Args:
            finish: The AgentFinish event containing final outputs
            **kwargs: Additional arguments including run_id
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            self._handle_agent_finish(run_id, finish)
        except Exception as e:
            logger.error(f"Error in on_agent_finish: {str(e)}")

    async def on_retry(
        self,
        retry_state: RetryCallState,
        **kwargs: Any,
    ) -> None:
        """Handle retry event asynchronously.
        
        This method is called when an operation is being retried. It creates a
        new span to track the retry attempt and stores information about the
        error that caused the retry.
        
        Args:
            retry_state: State information about the retry attempt
            **kwargs: Additional arguments including run_id
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        try:
            with _create_as_current_span(
                name="retry",
                kind=SpanKind.INTERNAL,
                attributes=_create_span_attributes(
                    run_id=run_id,
                    retry_attempt=retry_state.attempt_number,
                    error_type=type(retry_state.outcome.exception()).__name__,
                    error_message=str(retry_state.outcome.exception()),
                    **kwargs,
                ),
            ) as span:
                span.set_status(Status(StatusCode.ERROR))
                span.end()

        except Exception as e:
            logger.error(f"Error in on_retry: {str(e)}")

    async def on_llm_new_token(
        self,
        token: str,
        **kwargs: Any,
    ) -> None:
        """Handle new LLM token event asynchronously.
        
        This method is called when a new token is generated during streaming
        LLM responses. It updates the span with the accumulated response text.
        
        Args:
            token: The new token generated
            **kwargs: Additional arguments including run_id
        """
        run_id = kwargs.get("run_id")
        if not run_id:
            return

        span = self._llm_spans.get(run_id)
        if not span:
            return

        try:
            current_completion = span.get_attribute(LangchainAttributes.RESPONSE) or ""
            span.set_attribute(LangchainAttributes.RESPONSE, current_completion + token)
        except Exception as e:
            logger.error(f"Error in on_llm_new_token: {str(e)}") 