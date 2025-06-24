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
    extract_messages_from_output,
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

        self._active_graph_spans = {}

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

        with self._tracer.start_as_current_span("langgraph.StateGraph.__init__", kind=SpanKind.INTERNAL) as span:
            span.set_attributes(
                ensure_no_none_values(
                    {
                        SpanAttributes.AGENTOPS_SPAN_KIND: "workflow",
                        WorkflowAttributes.WORKFLOW_TYPE: "graph_initialization",
                        SpanAttributes.AGENTOPS_ENTITY_NAME: "StateGraph.__init__",
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

        with self._tracer.start_as_current_span("langgraph.StateGraph.compile", kind=SpanKind.INTERNAL) as span:
            span.set_attributes(
                ensure_no_none_values(
                    {
                        SpanAttributes.AGENTOPS_SPAN_KIND: "workflow",
                        WorkflowAttributes.WORKFLOW_TYPE: "graph_compilation",
                        SpanAttributes.AGENTOPS_ENTITY_NAME: "StateGraph.compile",
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
        if current_span and current_span.name == "langgraph.graph.execution":
            return wrapped(*args, **kwargs)

        with self._tracer.start_as_current_span("langgraph.graph.execution", kind=SpanKind.INTERNAL) as graph_span:
            graph_span.set_attributes(
                ensure_no_none_values(
                    {
                        SpanAttributes.AGENTOPS_SPAN_KIND: "workflow",
                        WorkflowAttributes.WORKFLOW_TYPE: "langgraph_graph",
                        SpanAttributes.AGENTOPS_ENTITY_NAME: "LangGraph",
                    }
                )
            )

            execution_state = {"executed_nodes": [], "message_count": 0, "final_response": None}

            with self._tracer.start_as_current_span("langgraph.Pregel.invoke", kind=SpanKind.INTERNAL) as span:
                span.set_attributes(
                    ensure_no_none_values(
                        {
                            SpanAttributes.AGENTOPS_SPAN_KIND: "operation",
                            SpanAttributes.AGENTOPS_ENTITY_NAME: "Pregel.invoke",
                            SpanAttributes.LLM_REQUEST_STREAMING: False,
                            "langgraph.execution.mode": "invoke",
                        }
                    )
                )

                try:
                    input_data = args[0] if args else kwargs.get("input", {})
                    messages = extract_messages_from_input(input_data)
                    if messages:
                        for i, msg in enumerate(messages[:3]):
                            content = get_message_content(msg)
                            role = get_message_role(msg)
                            if content:
                                span.set_attribute(f"gen_ai.prompt.{i}.content", content[:500])
                                span.set_attribute(f"gen_ai.prompt.{i}.role", role)

                    result = wrapped(*args, **kwargs)

                    output_messages = extract_messages_from_output(result)
                    if output_messages:
                        last_msg = output_messages[-1]
                        content = get_message_content(last_msg)
                        if content:
                            execution_state["final_response"] = content
                            span.set_attribute("gen_ai.response.0.content", content[:500])

                    span.set_status(Status(StatusCode.OK))
                    graph_span.set_status(Status(StatusCode.OK))

                    graph_span.set_attributes(
                        ensure_no_none_values(
                            {
                                "langgraph.graph.executed_nodes": json.dumps(execution_state["executed_nodes"]),
                                "langgraph.graph.node_execution_count": len(execution_state["executed_nodes"]),
                                "langgraph.graph.message_count": execution_state["message_count"],
                                "langgraph.graph.final_response": execution_state["final_response"],
                                "langgraph.graph.status": "success",
                            }
                        )
                    )

                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    graph_span.record_exception(e)
                    graph_span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

    def _wrap_stream(self, wrapped: Callable, instance: Any, args: Tuple, kwargs: Dict) -> Any:
        if not self._tracer:
            return wrapped(*args, **kwargs)

        current_span = trace.get_current_span()
        if current_span and current_span.name == "langgraph.graph.execution":
            return wrapped(*args, **kwargs)

        graph_span = self._tracer.start_span("langgraph.graph.execution", kind=SpanKind.INTERNAL)
        graph_span.set_attributes(
            ensure_no_none_values(
                {
                    SpanAttributes.AGENTOPS_SPAN_KIND: "workflow",
                    WorkflowAttributes.WORKFLOW_TYPE: "langgraph_streaming",
                    SpanAttributes.AGENTOPS_ENTITY_NAME: "LangGraph",
                }
            )
        )

        stream_span = self._tracer.start_span(
            "langgraph.Pregel.stream", kind=SpanKind.INTERNAL, context=trace.set_span_in_context(graph_span)
        )
        stream_span.set_attributes(
            ensure_no_none_values(
                {
                    SpanAttributes.AGENTOPS_SPAN_KIND: "operation",
                    SpanAttributes.AGENTOPS_ENTITY_NAME: "Pregel.stream",
                    SpanAttributes.LLM_REQUEST_STREAMING: True,
                    "langgraph.execution.mode": "stream",
                }
            )
        )

        execution_state = {"executed_nodes": [], "message_count": 0, "chunk_count": 0, "final_response": None}

        try:
            stream_gen = wrapped(*args, **kwargs)

            def stream_wrapper():
                try:
                    for chunk in stream_gen:
                        execution_state["chunk_count"] += 1

                        if isinstance(chunk, dict):
                            for key in chunk:
                                if key not in execution_state["executed_nodes"]:
                                    execution_state["executed_nodes"].append(key)

                                if key == "messages" and isinstance(chunk[key], list):
                                    execution_state["message_count"] += len(chunk[key])
                                    if chunk[key]:
                                        last_msg = chunk[key][-1]
                                        content = get_message_content(last_msg)
                                        if content:
                                            execution_state["final_response"] = content

                        yield chunk

                    stream_span.set_status(Status(StatusCode.OK))
                    graph_span.set_status(Status(StatusCode.OK))

                    graph_span.set_attributes(
                        ensure_no_none_values(
                            {
                                "langgraph.graph.executed_nodes": json.dumps(execution_state["executed_nodes"]),
                                "langgraph.graph.node_execution_count": len(execution_state["executed_nodes"]),
                                "langgraph.graph.message_count": execution_state["message_count"],
                                "langgraph.graph.total_chunks": execution_state["chunk_count"],
                                "langgraph.graph.final_response": execution_state["final_response"],
                                "langgraph.graph.status": "success",
                            }
                        )
                    )

                except Exception as e:
                    stream_span.record_exception(e)
                    stream_span.set_status(Status(StatusCode.ERROR, str(e)))
                    graph_span.record_exception(e)
                    graph_span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
                finally:
                    stream_span.end()
                    graph_span.end()

            return stream_wrapper()

        except Exception as e:
            stream_span.record_exception(e)
            stream_span.set_status(Status(StatusCode.ERROR, str(e)))
            stream_span.end()
            graph_span.record_exception(e)
            graph_span.set_status(Status(StatusCode.ERROR, str(e)))
            graph_span.end()
            raise

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
                    # Check if this node contains an LLM call
                    is_llm_node = self._detect_llm_node(original_func)

                    if is_llm_node:
                        with self._tracer.start_as_current_span(f"langgraph.llm.{key}", kind=SpanKind.CLIENT) as span:
                            span.set_attributes(
                                ensure_no_none_values(
                                    {
                                        SpanAttributes.AGENTOPS_SPAN_KIND: "llm",
                                        SpanAttributes.AGENTOPS_ENTITY_NAME: key,
                                        SpanAttributes.LLM_SYSTEM: "langgraph",
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
                    # Check if this node contains an LLM call
                    is_llm_node = self._detect_llm_node(original_func)

                    if is_llm_node:
                        with self._tracer.start_as_current_span(f"langgraph.llm.{key}", kind=SpanKind.CLIENT) as span:
                            span.set_attributes(
                                ensure_no_none_values(
                                    {
                                        SpanAttributes.AGENTOPS_SPAN_KIND: "llm",
                                        SpanAttributes.AGENTOPS_ENTITY_NAME: key,
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
        except Exception:
            # Don't fail the span if we can't extract info
            pass
