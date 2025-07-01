from functools import wraps
from typing import Any, Callable, Collection, Dict, Optional, Tuple
import json
import inspect

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode, get_tracer
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.utils import unwrap
from wrapt import wrap_function_wrapper

from agentops.semconv import (
    SpanAttributes,
    WorkflowAttributes,
    MessageAttributes,
)
from .attributes import (
    ensure_no_none_values,
    set_graph_attributes,
    extract_messages_from_input,
    get_message_content,
    get_message_role,
)

import sys

if "typing_extensions" not in sys.modules:
    from unittest import mock

    sys.modules["typing_extensions"] = mock.MagicMock()


class LanggraphInstrumentor(BaseInstrumentor):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.config = config or {}
        self._tracer = None

    def instrumentation_dependencies(self) -> Collection[str]:
        return ["langgraph >= 0.0.1"]

    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get("tracer_provider")
        self._tracer = get_tracer("agentops.instrumentation.agentic.langgraph", "0.1.0", tracer_provider)

        # Initialize context variable for tracking graph executions
        import contextvars

        self._current_graph_execution = contextvars.ContextVar("current_graph_execution", default=None)

        wrap_function_wrapper("langgraph.graph.state", "StateGraph.__init__", self._wrap_state_graph_init)

        wrap_function_wrapper("langgraph.graph.state", "StateGraph.compile", self._wrap_state_graph_compile)

        wrap_function_wrapper("langgraph.pregel", "Pregel.invoke", self._wrap_invoke)

        wrap_function_wrapper("langgraph.pregel", "Pregel.stream", self._wrap_stream)

        wrap_function_wrapper("langgraph.graph.state", "StateGraph.add_node", self._wrap_add_node)

    def _uninstrument(self, **kwargs):
        unwrap("langgraph.graph.state", "StateGraph.__init__")
        unwrap("langgraph.graph.state", "StateGraph.compile")
        unwrap("langgraph.pregel", "Pregel.invoke")
        unwrap("langgraph.pregel", "Pregel.stream")
        unwrap("langgraph.graph.state", "StateGraph.add_node")

    def _wrap_state_graph_init(self, wrapped: Callable, instance: Any, args: Tuple, kwargs: Dict) -> Any:
        if not self._tracer:
            return wrapped(*args, **kwargs)

        with self._tracer.start_as_current_span("langgraph.graph.initialize", kind=SpanKind.INTERNAL) as span:
            span.set_attributes(
                ensure_no_none_values(
                    {
                        SpanAttributes.AGENTOPS_SPAN_KIND: "workflow",
                        WorkflowAttributes.WORKFLOW_TYPE: "graph_initialization",
                        SpanAttributes.AGENTOPS_ENTITY_NAME: "Graph Initialization",
                    }
                )
            )

            try:
                result = wrapped(*args, **kwargs)

                instance._langgraph_instrumented = True
                instance._langgraph_nodes = []
                instance._langgraph_edges = []

                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    def _wrap_state_graph_compile(self, wrapped: Callable, instance: Any, args: Tuple, kwargs: Dict) -> Any:
        if not self._tracer:
            return wrapped(*args, **kwargs)

        with self._tracer.start_as_current_span("langgraph.graph.compile", kind=SpanKind.INTERNAL) as span:
            span.set_attributes(
                ensure_no_none_values(
                    {
                        SpanAttributes.AGENTOPS_SPAN_KIND: "workflow",
                        WorkflowAttributes.WORKFLOW_TYPE: "graph_compilation",
                        SpanAttributes.AGENTOPS_ENTITY_NAME: "Graph Compilation",
                        SpanAttributes.LLM_SYSTEM: "langgraph",
                    }
                )
            )

            try:
                result = wrapped(*args, **kwargs)

                nodes = []
                edges = []

                if hasattr(instance, "nodes"):
                    nodes = list(instance.nodes.keys()) if hasattr(instance.nodes, "keys") else []

                if hasattr(instance, "edges") and hasattr(instance.edges, "items"):
                    for source, targets in instance.edges.items():
                        if isinstance(targets, dict):
                            for target in targets.values():
                                edges.append(f"{source}->{target}")
                        elif isinstance(targets, list):
                            for target in targets:
                                edges.append(f"{source}->{target}")

                set_graph_attributes(span, nodes, edges)

                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    def _wrap_invoke(self, wrapped: Callable, instance: Any, args: Tuple, kwargs: Dict) -> Any:
        if not self._tracer:
            return wrapped(*args, **kwargs)

        current_span = trace.get_current_span()
        if current_span and current_span.name == "langgraph.workflow.execute":
            return wrapped(*args, **kwargs)

        with self._tracer.start_as_current_span("langgraph.workflow.execute", kind=SpanKind.INTERNAL) as span:
            span.set_attributes(
                ensure_no_none_values(
                    {
                        SpanAttributes.AGENTOPS_SPAN_KIND: "workflow",
                        WorkflowAttributes.WORKFLOW_TYPE: "langgraph_invoke",
                        SpanAttributes.AGENTOPS_ENTITY_NAME: "Workflow Execution",
                        SpanAttributes.LLM_REQUEST_STREAMING: False,
                        "langgraph.execution.mode": "invoke",
                    }
                )
            )

            execution_state = {"executed_nodes": [], "message_count": 0, "final_response": None}

            # Set the current execution state in context
            token = self._current_graph_execution.set(execution_state)

            try:
                input_data = args[0] if args else kwargs.get("input", {})
                messages = extract_messages_from_input(input_data)
                if messages:
                    execution_state["message_count"] = len(messages)
                    for i, msg in enumerate(messages[:3]):
                        content = get_message_content(msg)
                        role = get_message_role(msg)
                        if content:
                            span.set_attribute(f"gen_ai.prompt.{i}.content", content[:500])
                            span.set_attribute(f"gen_ai.prompt.{i}.role", role)

                result = wrapped(*args, **kwargs)

                # Extract execution information from result
                if isinstance(result, dict):
                    # Check for messages in result
                    if "messages" in result:
                        output_messages = result["messages"]
                        if isinstance(output_messages, list):
                            # Count all messages in the result
                            total_messages = len([msg for msg in output_messages if hasattr(msg, "content")])
                            execution_state["message_count"] = total_messages

                            if output_messages:
                                # Find the last non-tool message
                                for msg in reversed(output_messages):
                                    if hasattr(msg, "content") and not hasattr(msg, "tool_call_id"):
                                        content = get_message_content(msg)
                                        if content:
                                            execution_state["final_response"] = content
                                            span.set_attribute("gen_ai.response.0.content", content[:500])
                                            break

                # Capture final execution state before returning
                final_executed_nodes = list(execution_state["executed_nodes"])  # Copy the list
                final_node_count = len(final_executed_nodes)
                final_message_count = execution_state["message_count"]
                final_response = execution_state["final_response"]

                span.set_status(Status(StatusCode.OK))

                span.set_attributes(
                    ensure_no_none_values(
                        {
                            "langgraph.graph.executed_nodes": json.dumps(final_executed_nodes),
                            "langgraph.graph.node_execution_count": final_node_count,
                            "langgraph.graph.message_count": final_message_count,
                            "langgraph.graph.final_response": final_response,
                            "langgraph.graph.status": "success",
                        }
                    )
                )

                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
            finally:
                # Reset the context
                self._current_graph_execution.reset(token)

    def _wrap_stream(self, wrapped: Callable, instance: Any, args: Tuple, kwargs: Dict) -> Any:
        if not self._tracer:
            return wrapped(*args, **kwargs)

        current_span = trace.get_current_span()
        if current_span and current_span.name == "langgraph.workflow.execute":
            return wrapped(*args, **kwargs)

        span = self._tracer.start_span("langgraph.workflow.execute", kind=SpanKind.INTERNAL)
        span.set_attributes(
            ensure_no_none_values(
                {
                    SpanAttributes.AGENTOPS_SPAN_KIND: "workflow",
                    WorkflowAttributes.WORKFLOW_TYPE: "langgraph_stream",
                    SpanAttributes.AGENTOPS_ENTITY_NAME: "Workflow Stream",
                    SpanAttributes.LLM_REQUEST_STREAMING: True,
                    "langgraph.execution.mode": "stream",
                }
            )
        )

        execution_state = {"executed_nodes": [], "message_count": 0, "chunk_count": 0, "final_response": None}

        # Set the current execution state in context
        token = self._current_graph_execution.set(execution_state)

        try:
            # Extract input messages
            input_data = args[0] if args else kwargs.get("input", {})
            messages = extract_messages_from_input(input_data)
            if messages:
                execution_state["message_count"] = len(messages)
                for i, msg in enumerate(messages[:3]):
                    content = get_message_content(msg)
                    role = get_message_role(msg)
                    if content:
                        span.set_attribute(f"gen_ai.prompt.{i}.content", content[:500])
                        span.set_attribute(f"gen_ai.prompt.{i}.role", role)

            stream_gen = wrapped(*args, **kwargs)

            def stream_wrapper():
                try:
                    for chunk in stream_gen:
                        execution_state["chunk_count"] += 1

                        if isinstance(chunk, dict):
                            # Debug: print chunk structure
                            # print(f"DEBUG: Chunk keys: {list(chunk.keys())}")

                            for key in chunk:
                                # Track node executions (excluding special keys)
                                if (
                                    key not in ["__start__", "__end__", "__interrupt__"]
                                    and key not in execution_state["executed_nodes"]
                                ):
                                    execution_state["executed_nodes"].append(key)

                                # Track messages in the chunk value
                                chunk_value = chunk[key]
                                if isinstance(chunk_value, dict):
                                    # Check for messages in the chunk value
                                    if "messages" in chunk_value:
                                        msg_list = chunk_value["messages"]
                                        if isinstance(msg_list, list):
                                            execution_state["message_count"] += len(msg_list)
                                            for msg in msg_list:
                                                content = get_message_content(msg)
                                                if content:
                                                    execution_state["final_response"] = content
                                elif key == "messages" and isinstance(chunk_value, list):
                                    # Sometimes messages might be directly in the chunk
                                    execution_state["message_count"] += len(chunk_value)
                                    for msg in chunk_value:
                                        content = get_message_content(msg)
                                        if content:
                                            execution_state["final_response"] = content

                        yield chunk

                    # Capture final execution state before ending
                    final_executed_nodes = list(execution_state["executed_nodes"])
                    final_node_count = len(final_executed_nodes)
                    final_message_count = execution_state["message_count"]
                    final_chunk_count = execution_state["chunk_count"]
                    final_response = execution_state["final_response"]

                    span.set_status(Status(StatusCode.OK))

                    span.set_attributes(
                        ensure_no_none_values(
                            {
                                "langgraph.graph.executed_nodes": json.dumps(final_executed_nodes),
                                "langgraph.graph.node_execution_count": final_node_count,
                                "langgraph.graph.message_count": final_message_count,
                                "langgraph.graph.total_chunks": final_chunk_count,
                                "langgraph.graph.final_response": final_response,
                                "langgraph.graph.status": "success",
                            }
                        )
                    )

                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
                finally:
                    span.end()

            return stream_wrapper()

        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.end()
            raise
        finally:
            # Reset the context
            self._current_graph_execution.reset(token)

    def _wrap_add_node(self, wrapped: Callable, instance: Any, args: Tuple, kwargs: Dict) -> Any:
        if not self._tracer:
            return wrapped(*args, **kwargs)

        # Get node name and function
        if args:
            key = args[0]
            action = args[1] if len(args) > 1 else kwargs.get("action")
        else:
            key = kwargs.get("key")
            action = kwargs.get("action")

        if not action:
            return wrapped(*args, **kwargs)

        # Create wrapped node function that instruments LLM calls
        def create_wrapped_node(original_func):
            if inspect.iscoroutinefunction(original_func):

                @wraps(original_func)
                async def wrapped_node_async(state):
                    # Track node execution in parent graph span
                    self._track_node_execution(key)

                    # Check if this node contains an LLM call
                    is_llm_node = self._detect_llm_node(original_func)

                    if is_llm_node:
                        with self._tracer.start_as_current_span("langgraph.node.execute", kind=SpanKind.CLIENT) as span:
                            span.set_attributes(
                                ensure_no_none_values(
                                    {
                                        SpanAttributes.AGENTOPS_SPAN_KIND: "llm",
                                        SpanAttributes.AGENTOPS_ENTITY_NAME: f"Node: {key}",
                                        SpanAttributes.LLM_SYSTEM: "langgraph",
                                        "langgraph.node.name": key,
                                    }
                                )
                            )

                            try:
                                # Call the original function
                                result = await original_func(state)

                                # Extract LLM information from the result
                                self._extract_llm_info_from_result(span, state, result)

                                span.set_status(Status(StatusCode.OK))
                                return result
                            except Exception as e:
                                span.record_exception(e)
                                span.set_status(Status(StatusCode.ERROR, str(e)))
                                raise
                    else:
                        # Non-LLM node, just execute normally
                        return await original_func(state)
            else:

                @wraps(original_func)
                def wrapped_node_sync(state):
                    # Track node execution in parent graph span
                    self._track_node_execution(key)

                    # Check if this node contains an LLM call
                    is_llm_node = self._detect_llm_node(original_func)

                    if is_llm_node:
                        with self._tracer.start_as_current_span("langgraph.node.execute", kind=SpanKind.CLIENT) as span:
                            span.set_attributes(
                                ensure_no_none_values(
                                    {
                                        SpanAttributes.AGENTOPS_SPAN_KIND: "llm",
                                        SpanAttributes.AGENTOPS_ENTITY_NAME: f"Node: {key}",
                                        SpanAttributes.LLM_SYSTEM: "langgraph",
                                    }
                                )
                            )

                            try:
                                # Call the original function
                                result = original_func(state)

                                # Extract LLM information from the result
                                self._extract_llm_info_from_result(span, state, result)

                                span.set_status(Status(StatusCode.OK))
                                return result
                            except Exception as e:
                                span.record_exception(e)
                                span.set_status(Status(StatusCode.ERROR, str(e)))
                                raise
                    else:
                        # Non-LLM node, just execute normally
                        return original_func(state)

                return wrapped_node_sync

            return wrapped_node_async if inspect.iscoroutinefunction(original_func) else wrapped_node_sync

        # Wrap the action function
        wrapped_action = create_wrapped_node(action)

        # Call the original add_node with the wrapped action
        if args and len(args) > 1:
            new_args = (args[0], wrapped_action) + args[2:]
            return wrapped(*new_args, **kwargs)
        else:
            kwargs["action"] = wrapped_action
            return wrapped(*args, **kwargs)

    def _track_node_execution(self, node_name: str) -> None:
        """Track node execution in the active graph span."""
        # Use context variable to track the current execution
        if hasattr(self, "_current_graph_execution"):
            execution_state = self._current_graph_execution.get()
            if execution_state and node_name not in execution_state["executed_nodes"]:
                execution_state["executed_nodes"].append(node_name)

    def _detect_llm_node(self, func: Callable) -> bool:
        """Detect if a node function contains LLM calls."""
        try:
            # Get the source code of the function
            source = inspect.getsource(func)

            # Check for common LLM patterns
            llm_patterns = [
                "ChatOpenAI",
                "ChatAnthropic",
                "ChatGoogleGenerativeAI",
                ".invoke(",
                ".ainvoke(",
                ".stream(",
                ".astream(",
                "llm.",
                "model.",
                "chat.",
            ]

            for pattern in llm_patterns:
                if pattern in source:
                    return True

            # Check if function has 'llm' or 'model' in its local variables
            if hasattr(func, "__code__"):
                local_vars = func.__code__.co_varnames
                if any(var in ["llm", "model", "chat"] for var in local_vars):
                    return True

        except Exception:
            # If we can't inspect the source, assume it might be an LLM node
            pass

        return False

    def _extract_llm_info_from_result(self, span: Any, state: Dict, result: Any) -> None:
        """Extract LLM information from the node execution result."""
        try:
            # Extract messages from state
            if isinstance(state, dict) and "messages" in state:
                messages = state["messages"]
                # Set input messages
                for i, msg in enumerate(messages[-5:]):  # Last 5 messages as context
                    if hasattr(msg, "content"):
                        span.set_attribute(MessageAttributes.PROMPT_CONTENT.format(i=i), str(msg.content)[:1000])
                    if hasattr(msg, "role"):
                        span.set_attribute(MessageAttributes.PROMPT_ROLE.format(i=i), msg.role)
                    elif hasattr(msg, "type"):
                        span.set_attribute(MessageAttributes.PROMPT_ROLE.format(i=i), msg.type)

            # Extract messages from result
            if isinstance(result, dict) and "messages" in result:
                output_messages = result["messages"]
                if output_messages:
                    last_msg = output_messages[-1] if isinstance(output_messages, list) else output_messages

                    # Extract model information from message if available
                    if hasattr(last_msg, "response_metadata"):
                        metadata = last_msg.response_metadata
                        if isinstance(metadata, dict):
                            if "model_name" in metadata:
                                span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, metadata["model_name"])
                                span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, metadata["model_name"])
                            elif "model" in metadata:
                                span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, metadata["model"])
                                span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, metadata["model"])

                            # Token usage
                            if "token_usage" in metadata:
                                usage = metadata["token_usage"]
                                if isinstance(usage, dict):
                                    if "prompt_tokens" in usage:
                                        span.set_attribute(
                                            SpanAttributes.LLM_USAGE_PROMPT_TOKENS, usage["prompt_tokens"]
                                        )
                                    if "completion_tokens" in usage:
                                        span.set_attribute(
                                            SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, usage["completion_tokens"]
                                        )
                                    if "total_tokens" in usage:
                                        span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, usage["total_tokens"])

                            # Response ID
                            if "id" in metadata and metadata["id"] is not None:
                                span.set_attribute(SpanAttributes.LLM_RESPONSE_ID, metadata["id"])

                            # Finish reason
                            if "finish_reason" in metadata:
                                span.set_attribute(
                                    MessageAttributes.COMPLETION_FINISH_REASON.format(i=0), metadata["finish_reason"]
                                )

                    # Content
                    if hasattr(last_msg, "content"):
                        span.set_attribute(
                            MessageAttributes.COMPLETION_CONTENT.format(i=0), str(last_msg.content)[:1000]
                        )
                    if hasattr(last_msg, "role"):
                        span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), last_msg.role)

                    # Check for tool calls
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        for j, tool_call in enumerate(last_msg.tool_calls[:5]):
                            if hasattr(tool_call, "name"):
                                span.set_attribute(
                                    MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=j), tool_call.name
                                )
                            if hasattr(tool_call, "args"):
                                span.set_attribute(
                                    MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=0, j=j),
                                    json.dumps(tool_call.args)[:500],
                                )
                            if hasattr(tool_call, "id"):
                                span.set_attribute(
                                    MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=0, j=j), tool_call.id
                                )

                    # Additional attributes from message
                    if hasattr(last_msg, "id") and last_msg.id is not None:
                        span.set_attribute(SpanAttributes.LLM_RESPONSE_ID, last_msg.id)

                    # Usage information might be on the message itself
                    if hasattr(last_msg, "usage_metadata"):
                        usage = last_msg.usage_metadata
                        if hasattr(usage, "input_tokens"):
                            span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, usage.input_tokens)
                        if hasattr(usage, "output_tokens"):
                            span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, usage.output_tokens)
                        if hasattr(usage, "total_tokens"):
                            span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, usage.total_tokens)
        except Exception:
            # Don't fail the span if we can't extract info
            pass
