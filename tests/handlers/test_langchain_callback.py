"""Test suite for Langchain callback handlers.

This test suite verifies the functionality of both synchronous and asynchronous
Langchain callback handlers. It tests the following aspects:

1. Basic Functionality:
   - Handler initialization and configuration
   - Span creation and management
   - Attribute recording
   - Error handling

2. LLM Operations:
   - LLM start/end events
   - Token streaming
   - Error handling
   - Response processing

3. Chat Model Operations:
   - Chat model start/end events
   - Message handling
   - Response processing

4. Chain Operations:
   - Chain start/end events
   - Input/output handling
   - Error propagation

5. Tool Operations:
   - Tool start/end events
   - Input/output recording
   - Error handling

6. Retriever Operations:
   - Retriever start/end events
   - Query handling
   - Document processing

7. Agent Operations:
   - Agent action events
   - Tool usage tracking
   - Finish event handling

8. Error Scenarios:
   - Exception handling
   - Error propagation
   - Span error status

9. Async Functionality:
   - Async handler initialization
   - Async event handling
   - Async error handling

10. Edge Cases:
    - Missing run IDs
    - Invalid inputs
    - Stream handling
    - Retry scenarios

The tests use mock objects to simulate Langchain operations and verify that
the handlers correctly create and manage OpenTelemetry spans with appropriate
attributes and error handling.
""" 

import asyncio
from typing import Dict, Any, List
from uuid import UUID, uuid4
import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.trace import Status, StatusCode, SpanKind
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from langchain_core.agents import AgentFinish, AgentAction
from langchain_core.documents import Document
from langchain_core.outputs import ChatGenerationChunk, GenerationChunk, LLMResult, Generation
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, AIMessageChunk
from tenacity import RetryCallState

from agentops import init
from agentops.sdk.core import TracingCore
from agentops.integrations.langchain.callback_handler import (
    LangchainCallbackHandler,
    AsyncLangchainCallbackHandler,
)
from agentops.semconv import SpanKind
from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.langchain_attributes import LangchainAttributes


pytestmark = pytest.mark.asyncio


def get_model_from_kwargs(kwargs: dict) -> str:
    """Extract model name from kwargs."""
    if "model" in kwargs.get("invocation_params", {}):
        return kwargs["invocation_params"]["model"]
    elif "_type" in kwargs.get("invocation_params", {}):
        return kwargs["invocation_params"]["_type"]
    return "unknown_model"


@contextmanager
def _create_as_current_span(
    name: str,
    kind: SpanKind,
    attributes: Dict[str, Any] = None,
):
    """Create a span and set it as the current span."""
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(
        name,
        kind=kind,
        attributes=attributes or {},
    ) as span:
        yield span


@pytest.fixture(autouse=True)
def setup_agentops():
    """Initialize AgentOps client for testing."""
    init(api_key="test-api-key")
    yield
    # Cleanup will be handled by the test framework


@pytest.fixture
def tracer_provider():
    """Create a tracer provider with an in-memory exporter for testing."""
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    return provider, exporter


@pytest.fixture
def tracing_core():
    """Initialize TracingCore for testing."""
    core = TracingCore.get_instance()
    core.initialize(
        service_name="test_service",
    )
    yield core
    core.shutdown()


@pytest.fixture
def mock_client():
    """Create a mock AgentOps client."""
    with patch("agentops.Client") as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        client_instance.configure.return_value = None
        client_instance.init.return_value = None
        client_instance.current_session_ids = ["test-session-id"]
        yield client_instance


@pytest.fixture
def callback_handler(mock_client):
    """Create a callback handler with mocked client."""
    return LangchainCallbackHandler()


@pytest.fixture
def async_callback_handler(mock_client):
    """Create an async callback handler with mocked client."""
    return AsyncLangchainCallbackHandler()


@pytest.fixture
def test_run_ids():
    """Generate test run IDs."""
    return {
        "run_id": UUID("12345678-1234-5678-1234-567812345678"),
        "parent_run_id": UUID("87654321-4321-8765-4321-876543210987"),
    }


@pytest.fixture
def test_llm_inputs():
    """Generate test LLM inputs."""
    return {
        "serialized": {"name": "test-llm"},
        "prompts": ["test prompt"],
        "invocation_params": {"model": "test-model"},
    }


@pytest.fixture
def test_chain_inputs():
    """Generate test chain inputs."""
    return {
        "serialized": {"name": "test-chain"},
        "inputs": {"input": "test input"},
    }


@pytest.fixture
def test_tool_inputs():
    """Generate test tool inputs."""
    return {
        "serialized": {"name": "test-tool"},
        "input_str": "test input",
        "inputs": {"input": "test input"},
    }


@pytest.fixture
def test_agent_inputs():
    """Generate test agent inputs."""
    return {
        "action": AgentAction(
            tool="test-tool",
            tool_input="test input",
            log="test log",
        ),
        "finish": AgentFinish(
            return_values={"output": "test output"},
            log="test log",
        ),
    }


@pytest.fixture
def test_retry_state():
    """Generate test retry state."""
    state = MagicMock(spec=RetryCallState)
    state.attempt_number = 1
    state.outcome = MagicMock()
    state.outcome.exception.return_value = Exception("test error")
    return state


def test_llm_events(callback_handler, test_run_ids, test_llm_inputs):
    """Test LLM events."""
    # Test LLM start
    callback_handler.on_llm_start(
        **test_llm_inputs,
        **test_run_ids,
    )

    # Test LLM end
    response = LLMResult(
        generations=[[Generation(text="test response")]],
        llm_output={"token_usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}},
    )
    callback_handler.on_llm_end(
        response=response,
        **test_run_ids,
    )


def test_chain_events(callback_handler, test_run_ids, test_chain_inputs):
    """Test chain events."""
    # Test chain start
    callback_handler.on_chain_start(
        **test_chain_inputs,
        **test_run_ids,
    )

    # Test chain end
    callback_handler.on_chain_end(
        outputs={"output": "test output"},
        **test_run_ids,
    )


def test_tool_events(callback_handler, test_run_ids, test_tool_inputs):
    """Test tool events."""
    # Test tool start
    callback_handler.on_tool_start(
        **test_tool_inputs,
        **test_run_ids,
    )

    # Test tool end
    callback_handler.on_tool_end(
        output="test output",
        **test_run_ids,
    )


def test_agent_events(callback_handler, test_run_ids, test_agent_inputs):
    """Test agent events."""
    # Test agent action
    callback_handler.on_agent_action(
        action=test_agent_inputs["action"],
        **test_run_ids,
    )

    # Test agent finish
    callback_handler.on_agent_finish(
        finish=test_agent_inputs["finish"],
        **test_run_ids,
    )


def test_retry_events(callback_handler, test_run_ids, test_retry_state):
    """Test retry events."""
    callback_handler.on_retry(
        retry_state=test_retry_state,
        **test_run_ids,
    )


@pytest.mark.asyncio
async def test_async_llm_events(async_callback_handler, test_run_ids, test_llm_inputs):
    """Test async LLM events."""
    # Test LLM start
    await async_callback_handler.on_llm_start(
        **test_llm_inputs,
        **test_run_ids,
    )

    # Test LLM end
    response = LLMResult(
        generations=[[Generation(text="test response")]],
        llm_output={"token_usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}},
    )
    await async_callback_handler.on_llm_end(
        response=response,
        **test_run_ids,
    )


@pytest.mark.asyncio
async def test_async_chain_events(async_callback_handler, test_run_ids, test_chain_inputs):
    """Test async chain events."""
    # Test chain start
    await async_callback_handler.on_chain_start(
        **test_chain_inputs,
        **test_run_ids,
    )

    # Test chain end
    await async_callback_handler.on_chain_end(
        outputs={"output": "test output"},
        **test_run_ids,
    )


@pytest.mark.asyncio
async def test_async_tool_events(async_callback_handler, test_run_ids, test_tool_inputs):
    """Test async tool events."""
    # Test tool start
    await async_callback_handler.on_tool_start(
        **test_tool_inputs,
        **test_run_ids,
    )

    # Test tool end
    await async_callback_handler.on_tool_end(
        output="test output",
        **test_run_ids,
    )


@pytest.mark.asyncio
async def test_async_agent_events(async_callback_handler, test_run_ids, test_agent_inputs):
    """Test async agent events."""
    # Test agent action
    await async_callback_handler.on_agent_action(
        action=test_agent_inputs["action"],
        **test_run_ids,
    )

    # Test agent finish
    await async_callback_handler.on_agent_finish(
        finish=test_agent_inputs["finish"],
        **test_run_ids,
    )


@pytest.mark.asyncio
async def test_async_retry_events(async_callback_handler, test_run_ids, test_retry_state):
    """Test async retry events."""
    await async_callback_handler.on_retry(
        retry_state=test_retry_state,
        **test_run_ids,
    )


@pytest.fixture
def test_llm_responses():
    """Generate test LLM responses."""
    return {
        "text_response": LLMResult(
            generations=[[Generation(text="test response")]],
            llm_output={"token_usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}},
        ),
        "message_response": LLMResult(
            generations=[[ChatGenerationChunk(message=AIMessageChunk(content="test message"))]],
            llm_output={"token_usage": {"prompt_tokens": 5, "completion_tokens": 15, "total_tokens": 20}},
        ),
        "empty_response": LLMResult(
            generations=[],
            llm_output=None,
        ),
        "error_response": LLMResult(
            generations=[[Generation(text="error response")]],
            llm_output={"error": "test error"},
        ),
    }


@pytest.fixture
def test_chain_outputs():
    """Generate test chain outputs."""
    return {
        "simple_output": {"output": "test output"},
        "complex_output": {"output": {"nested": "value", "list": [1, 2, 3]}},
        "error_output": {"error": "test error"},
    }


@pytest.fixture
def test_tool_outputs():
    """Generate test tool outputs."""
    return {
        "success_output": "test output",
        "exception_output": "_Exception",
        "error_output": "error: test error",
    }


@pytest.fixture
def test_agent_sequences():
    """Generate test agent action sequences."""
    return {
        "single_action": [
            AgentAction(tool="tool1", tool_input="input1", log="log1"),
            AgentFinish(return_values={"output": "output1"}, log="finish1"),
        ],
        "multiple_actions": [
            AgentAction(tool="tool1", tool_input="input1", log="log1"),
            AgentAction(tool="tool2", tool_input="input2", log="log2"),
            AgentFinish(return_values={"output": "output2"}, log="finish2"),
        ],
        "error_action": [
            AgentAction(tool="error_tool", tool_input="error_input", log="error_log"),
            AgentFinish(return_values={"error": "test error"}, log="error_finish"),
        ],
    }


def test_llm_events_with_different_response_types(callback_handler, test_run_ids, test_llm_inputs, test_llm_responses):
    """Test LLM event handling with various response types and scenarios.
    
    This test verifies that the handler correctly processes:
    - LLM start events with different input configurations
    - LLM end events with different response types:
        * Text-based responses
        * Message-based responses (using AIMessageChunk)
        * Empty responses
        * Error responses
    - Streaming token updates
    - Error handling scenarios
    """
    # Test LLM start
    callback_handler.on_llm_start(
        **test_llm_inputs,
        **test_run_ids,
    )

    # Test different response types
    callback_handler.on_llm_end(
        response=test_llm_responses["text_response"],
        **test_run_ids,
    )

    # Test message-based response
    callback_handler.on_llm_end(
        response=test_llm_responses["message_response"],
        **test_run_ids,
    )

    # Test empty response
    callback_handler.on_llm_end(
        response=test_llm_responses["empty_response"],
        **test_run_ids,
    )

    # Test error response
    callback_handler.on_llm_end(
        response=test_llm_responses["error_response"],
        **test_run_ids,
    )

    # Test streaming tokens
    callback_handler.on_llm_new_token(
        token="test",
        **test_run_ids,
    )
    callback_handler.on_llm_new_token(
        token=" token",
        **test_run_ids,
    )

    # Test LLM error
    callback_handler.on_llm_error(
        error=Exception("test error"),
        **test_run_ids,
    )


def test_chain_events_with_metadata_and_outputs(callback_handler, test_run_ids, test_chain_inputs, test_chain_outputs):
    """Test chain event handling with metadata and various output formats.
    
    This test verifies that the handler correctly processes:
    - Chain start events with metadata
    - Chain end events with different output formats:
        * Simple key-value outputs
        * Complex nested outputs
        * Error outputs
    - Chain error handling
    """
    # Test chain start with metadata
    callback_handler.on_chain_start(
        **test_chain_inputs,
        metadata={"test": "metadata"},
        **test_run_ids,
    )

    # Test different output types
    callback_handler.on_chain_end(
        outputs=test_chain_outputs["simple_output"],
        **test_run_ids,
    )

    callback_handler.on_chain_end(
        outputs=test_chain_outputs["complex_output"],
        **test_run_ids,
    )

    # Test chain error
    callback_handler.on_chain_error(
        error=Exception("test error"),
        **test_run_ids,
    )


def test_tool_events_with_exceptions_and_errors(callback_handler, test_run_ids, test_tool_inputs, test_tool_outputs):
    """Test tool event handling with various input/output types and error scenarios.
    
    This test verifies that the handler correctly processes:
    - Tool start events with different input configurations
    - Tool end events with different output types:
        * Successful outputs
        * Exception outputs
        * Error outputs
    - Tool error handling
    """
    # Test tool start with different inputs
    callback_handler.on_tool_start(
        **{k: v for k, v in test_tool_inputs.items() if k != 'inputs'},
        **test_run_ids,
    )

    # Test different output types
    callback_handler.on_tool_end(
        output=test_tool_outputs["success_output"],
        **test_run_ids,
    )

    # Test exception tool
    callback_handler.on_tool_end(
        output=test_tool_outputs["exception_output"],
        name="_Exception",
        **test_run_ids,
    )

    # Test tool error
    callback_handler.on_tool_error(
        error=Exception("test error"),
        **test_run_ids,
    )


def test_agent_events_with_action_sequences(callback_handler, test_run_ids, test_agent_sequences):
    """Test agent event handling with different action sequences and scenarios.
    
    This test verifies that the handler correctly processes:
    - Single action sequences (action + finish)
    - Multiple action sequences (multiple actions + finish)
    - Error action sequences
    - Different types of agent actions and finishes
    """
    # Test single action sequence
    for action in test_agent_sequences["single_action"]:
        if isinstance(action, AgentAction):
            callback_handler.on_agent_action(
                action=action,
                **test_run_ids,
            )
        else:
            callback_handler.on_agent_finish(
                finish=action,
                **test_run_ids,
            )

    # Test multiple actions sequence
    for action in test_agent_sequences["multiple_actions"]:
        if isinstance(action, AgentAction):
            callback_handler.on_agent_action(
                action=action,
                **test_run_ids,
            )
        else:
            callback_handler.on_agent_finish(
                finish=action,
                **test_run_ids,
            )

    # Test error sequence
    for action in test_agent_sequences["error_action"]:
        if isinstance(action, AgentAction):
            callback_handler.on_agent_action(
                action=action,
                **test_run_ids,
            )
        else:
            callback_handler.on_agent_finish(
                finish=action,
                **test_run_ids,
            )


def test_retriever_events_with_documents(callback_handler, test_run_ids):
    """Test retriever event handling with document processing.
    
    This test verifies that the handler correctly processes:
    - Retriever start events with query information
    - Retriever end events with document results
    - Retriever error handling
    """
    # Test retriever start
    callback_handler.on_retriever_start(
        serialized={"name": "test-retriever"},
        query="test query",
        **test_run_ids,
    )

    # Test retriever end
    callback_handler.on_retriever_end(
        documents=[Document(page_content="test content")],
        **test_run_ids,
    )

    # Test retriever error
    callback_handler.on_retriever_error(
        error=Exception("test error"),
        **test_run_ids,
    )


def test_retry_events_with_different_states(callback_handler, test_run_ids, test_retry_state):
    """Test retry event handling with different retry states and error types.
    
    This test verifies that the handler correctly processes:
    - Retry events with standard retry states
    - Retry events with different error types
    - Retry state information tracking
    """
    # Test retry with different states
    callback_handler.on_retry(
        retry_state=test_retry_state,
        **test_run_ids,
    )

    # Test retry with different error types
    error_state = MagicMock(spec=RetryCallState)
    error_state.attempt_number = 2
    error_state.outcome = MagicMock()
    error_state.outcome.exception.return_value = ValueError("test error")
    callback_handler.on_retry(
        retry_state=error_state,
        **test_run_ids,
    )


@pytest.mark.asyncio
async def test_async_llm_events_with_different_response_types(async_callback_handler, test_run_ids, test_llm_inputs, test_llm_responses):
    """Test async LLM event handling with various response types and scenarios.
    
    This test verifies that the async handler correctly processes:
    - Async LLM start events with different input configurations
    - Async LLM end events with different response types:
        * Text-based responses
        * Message-based responses (using AIMessageChunk)
        * Empty responses
        * Error responses
    - Async streaming token updates
    - Async error handling scenarios
    """
    # Test LLM start
    await async_callback_handler.on_llm_start(
        **test_llm_inputs,
        **test_run_ids,
    )

    # Test different response types
    await async_callback_handler.on_llm_end(
        response=test_llm_responses["text_response"],
        **test_run_ids,
    )

    # Test message-based response
    await async_callback_handler.on_llm_end(
        response=test_llm_responses["message_response"],
        **test_run_ids,
    )

    # Test empty response
    await async_callback_handler.on_llm_end(
        response=test_llm_responses["empty_response"],
        **test_run_ids,
    )

    # Test error response
    await async_callback_handler.on_llm_end(
        response=test_llm_responses["error_response"],
        **test_run_ids,
    )

    # Test streaming tokens
    await async_callback_handler.on_llm_new_token(
        token="test",
        **test_run_ids,
    )
    await async_callback_handler.on_llm_new_token(
        token=" token",
        **test_run_ids,
    )

    # Test LLM error
    await async_callback_handler.on_llm_error(
        error=Exception("test error"),
        **test_run_ids,
    )


@pytest.mark.asyncio
async def test_async_chain_events_with_metadata_and_outputs(async_callback_handler, test_run_ids, test_chain_inputs, test_chain_outputs):
    """Test async chain event handling with metadata and various output formats.
    
    This test verifies that the async handler correctly processes:
    - Async chain start events with metadata
    - Async chain end events with different output formats:
        * Simple key-value outputs
        * Complex nested outputs
        * Error outputs
    - Async chain error handling
    """
    # Test chain start with metadata
    await async_callback_handler.on_chain_start(
        **test_chain_inputs,
        metadata={"test": "metadata"},
        **test_run_ids,
    )

    # Test different output types
    await async_callback_handler.on_chain_end(
        outputs=test_chain_outputs["simple_output"],
        **test_run_ids,
    )

    await async_callback_handler.on_chain_end(
        outputs=test_chain_outputs["complex_output"],
        **test_run_ids,
    )

    # Test chain error
    await async_callback_handler.on_chain_error(
        error=Exception("test error"),
        **test_run_ids,
    )


@pytest.mark.asyncio
async def test_async_tool_events_with_exceptions_and_errors(async_callback_handler, test_run_ids, test_tool_inputs, test_tool_outputs):
    """Test async tool event handling with various input/output types and error scenarios.
    
    This test verifies that the async handler correctly processes:
    - Async tool start events with different input configurations
    - Async tool end events with different output types:
        * Successful outputs
        * Exception outputs
        * Error outputs
    - Async tool error handling
    """
    # Test tool start with different inputs
    await async_callback_handler.on_tool_start(
        **{k: v for k, v in test_tool_inputs.items() if k != 'inputs'},
        **test_run_ids,
    )

    # Test different output types
    await async_callback_handler.on_tool_end(
        output=test_tool_outputs["success_output"],
        **test_run_ids,
    )

    # Test exception tool
    await async_callback_handler.on_tool_end(
        output=test_tool_outputs["exception_output"],
        name="_Exception",
        **test_run_ids,
    )

    # Test tool error
    await async_callback_handler.on_tool_error(
        error=Exception("test error"),
        **test_run_ids,
    )


@pytest.mark.asyncio
async def test_async_agent_events_with_action_sequences(async_callback_handler, test_run_ids, test_agent_sequences):
    """Test async agent event handling with different action sequences and scenarios.
    
    This test verifies that the async handler correctly processes:
    - Async single action sequences (action + finish)
    - Async multiple action sequences (multiple actions + finish)
    - Async error action sequences
    - Async different types of agent actions and finishes
    """
    # Test single action sequence
    for action in test_agent_sequences["single_action"]:
        if isinstance(action, AgentAction):
            await async_callback_handler.on_agent_action(
                action=action,
                **test_run_ids,
            )
        else:
            await async_callback_handler.on_agent_finish(
                finish=action,
                **test_run_ids,
            )

    # Test multiple actions sequence
    for action in test_agent_sequences["multiple_actions"]:
        if isinstance(action, AgentAction):
            await async_callback_handler.on_agent_action(
                action=action,
                **test_run_ids,
            )
        else:
            await async_callback_handler.on_agent_finish(
                finish=action,
                **test_run_ids,
            )

    # Test error sequence
    for action in test_agent_sequences["error_action"]:
        if isinstance(action, AgentAction):
            await async_callback_handler.on_agent_action(
                action=action,
                **test_run_ids,
            )
        else:
            await async_callback_handler.on_agent_finish(
                finish=action,
                **test_run_ids,
            )


@pytest.mark.asyncio
async def test_async_retriever_events_with_documents(async_callback_handler, test_run_ids):
    """Test async retriever event handling with document processing.
    
    This test verifies that the async handler correctly processes:
    - Async retriever start events with query information
    - Async retriever end events with document results
    - Async retriever error handling
    """
    # Test retriever start
    await async_callback_handler.on_retriever_start(
        serialized={"name": "test-retriever"},
        query="test query",
        **test_run_ids,
    )

    # Test retriever end
    await async_callback_handler.on_retriever_end(
        documents=[Document(page_content="test content")],
        **test_run_ids,
    )

    # Test retriever error
    await async_callback_handler.on_retriever_error(
        error=Exception("test error"),
        **test_run_ids,
    )


@pytest.mark.asyncio
async def test_async_retry_events_with_different_states(async_callback_handler, test_run_ids, test_retry_state):
    """Test async retry event handling with different retry states and error types.
    
    This test verifies that the async handler correctly processes:
    - Async retry events with standard retry states
    - Async retry events with different error types
    - Async retry state information tracking
    """
    # Test retry with different states
    await async_callback_handler.on_retry(
        retry_state=test_retry_state,
        **test_run_ids,
    )

    # Test retry with different error types
    error_state = MagicMock(spec=RetryCallState)
    error_state.attempt_number = 2
    error_state.outcome = MagicMock()
    error_state.outcome.exception.return_value = ValueError("test error")
    await async_callback_handler.on_retry(
        retry_state=error_state,
        **test_run_ids,
    ) 