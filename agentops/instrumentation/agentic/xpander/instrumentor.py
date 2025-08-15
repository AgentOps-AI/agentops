"""Xpander SDK instrumentation for AgentOps.

This module provides instrumentation for the Xpander SDK, which uses JSII to convert
TypeScript code to Python at runtime. The instrumentation tracks agent sessions,
tool executions, and LLM interactions.

MODIFIED VERSION: Using existing AgentOps utilities where possible while keeping
runtime-specific instrumentation logic that cannot be replaced.

REPLACEMENTS MADE:
✅ Span creation: Using tracer.make_span() instead of manual span creation
✅ Error handling: Using _finish_span_success/_finish_span_error utilities
✅ Attribute management: Using existing SpanAttributeManager
✅ Serialization: Using safe_serialize and model_to_dict utilities
✅ Attribute setting: Using _update_span utility

RUNTIME-SPECIFIC LOGIC KEPT (Cannot be replaced):
❌ Method wrapping: Runtime method creation requires custom hooks
❌ Context persistence: XpanderContext must handle runtime object lifecycle
❌ Agent detection: Custom logic for dynamically created agents
"""

import logging
import time
import json
from typing import Any, Optional
from opentelemetry.metrics import Meter
from opentelemetry.trace import SpanKind as OTelSpanKind
from opentelemetry import trace

# Use existing AgentOps utilities
from agentops.instrumentation.common import (
    CommonInstrumentor,
    InstrumentorConfig,
    StandardMetrics,
)
from agentops.instrumentation.common.span_management import SpanAttributeManager
from agentops.instrumentation.common.wrappers import _finish_span_success, _finish_span_error, _update_span
from agentops.helpers.serialization import safe_serialize, model_to_dict
from agentops.sdk.core import tracer
from agentops.instrumentation.agentic.xpander.context import XpanderContext
from agentops.semconv import SpanAttributes, SpanKind, ToolAttributes
from agentops.semconv.message import MessageAttributes

# Use existing OpenAI attribute extraction patterns (lazy import to avoid circular imports)
# from agentops.instrumentation.providers.openai.attributes.common import (
#     get_response_attributes,
# )

logger = logging.getLogger(__name__)

_instruments = ("xpander-sdk >= 1.0.0",)


# Use existing AgentOps utility instead of custom implementation
def safe_set_attribute(span, key: str, value: Any) -> None:
    """Set attribute on span using existing AgentOps utility."""
    try:
        _update_span(span, {key: value})
    except Exception as e:
        logger.warning(f"Failed to set attribute {key}: {e}")


class XpanderInstrumentor(CommonInstrumentor):
    """Instrumentor for Xpander SDK interactions."""

    def __init__(self, config: Optional[InstrumentorConfig] = None):
        if config is None:
            config = InstrumentorConfig(
                library_name="xpander-sdk", library_version="1.0.0", dependencies=_instruments, metrics_enabled=True
            )
        super().__init__(config)
        self._context = XpanderContext()
        self._tracer = None
        # Use existing AgentOps attribute manager
        self._attribute_manager = SpanAttributeManager("xpander-service", "production")

    def _get_session_id_from_agent(self, agent) -> str:
        """Generate consistent session ID from agent."""
        # First try to get memory_thread_id from agent context if available
        if hasattr(agent, "memory_thread_id"):
            return f"session_{agent.memory_thread_id}"

        # Check for execution context
        if hasattr(agent, "execution") and hasattr(agent.execution, "memory_thread_id"):
            return f"session_{agent.execution.memory_thread_id}"

        # Fallback to agent-based ID
        agent_name = getattr(agent, "name", "unknown")
        agent_id = getattr(agent, "id", "unknown")
        return f"agent_{agent_name}_{agent_id}"

    def _extract_session_id(self, execution, agent=None) -> str:
        """Extract session ID from execution data."""
        if isinstance(execution, dict):
            if "memory_thread_id" in execution:
                return f"session_{execution['memory_thread_id']}"
            elif "thread_id" in execution:
                return f"session_{execution['thread_id']}"
            elif "session_id" in execution:
                return f"session_{execution['session_id']}"

        # Fallback to agent-based ID if available
        if agent:
            return self._get_session_id_from_agent(agent)

        # Last resort fallback
        return f"session_{int(time.time())}"

    def _extract_tool_name(self, tool_call) -> str:
        """Extract tool name from tool call."""
        # Handle different tool call formats
        if hasattr(tool_call, "function_name"):
            return tool_call.function_name
        elif hasattr(tool_call, "function") and hasattr(tool_call.function, "name"):
            return tool_call.function.name
        elif hasattr(tool_call, "name"):
            return tool_call.name
        elif isinstance(tool_call, dict):
            if "function" in tool_call:
                return tool_call["function"].get("name", "unknown")
            elif "function_name" in tool_call:
                return tool_call["function_name"]
            elif "name" in tool_call:
                return tool_call["name"]

        # Try to extract from string representation
        import re

        patterns = [
            r'function[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]',
            r'name[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]',
            r"([a-zA-Z_][a-zA-Z0-9_]*)\.tool",
            r'function_name[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]',
        ]

        tool_str = str(tool_call)
        for pattern in patterns:
            match = re.search(pattern, tool_str, re.IGNORECASE)
            if match:
                return match.group(1)

        return "unknown"

    def _extract_tool_params(self, tool_call) -> dict:
        """Extract tool parameters from tool call."""
        # Handle different parameter formats
        if hasattr(tool_call, "function") and hasattr(tool_call.function, "arguments"):
            try:
                args = tool_call.function.arguments
                if isinstance(args, str):
                    return json.loads(args)
                elif isinstance(args, dict):
                    return args
            except (json.JSONDecodeError, AttributeError):
                pass
        elif hasattr(tool_call, "arguments"):
            try:
                args = tool_call.arguments
                if isinstance(args, str):
                    return json.loads(args)
                elif isinstance(args, dict):
                    return args
            except (json.JSONDecodeError, AttributeError):
                pass
        elif isinstance(tool_call, dict):
            if "function" in tool_call:
                args = tool_call["function"].get("arguments", "{}")
                try:
                    return json.loads(args) if isinstance(args, str) else args
                except json.JSONDecodeError:
                    pass
            elif "arguments" in tool_call:
                args = tool_call["arguments"]
                try:
                    return json.loads(args) if isinstance(args, str) else args
                except json.JSONDecodeError:
                    pass

        return {}

    def _extract_llm_data_from_messages(self, messages) -> dict:
        """Extract LLM metadata from messages."""
        data = {}

        if isinstance(messages, dict):
            # Direct model and usage fields
            if "model" in messages:
                data["model"] = messages["model"]
            if "usage" in messages:
                data["usage"] = messages["usage"]

            # Check in choices array (OpenAI format)
            if "choices" in messages and messages["choices"]:
                choice = messages["choices"][0]
                if "message" in choice:
                    message = choice["message"]
                    if "model" in message:
                        data["model"] = message["model"]

        elif isinstance(messages, list):
            # Look for assistant messages with metadata
            for msg in messages:
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    if "model" in msg:
                        data["model"] = msg["model"]
                    if "usage" in msg:
                        data["usage"] = msg["usage"]
                    break

        # Try to extract from any nested structures
        if not data and hasattr(messages, "__dict__"):
            msg_dict = messages.__dict__
            if "model" in msg_dict:
                data["model"] = msg_dict["model"]
            if "usage" in msg_dict:
                data["usage"] = msg_dict["usage"]

        return data

    def _extract_and_set_openai_message_attributes(self, span, messages, result, agent=None):
        """Extract and set OpenAI message attributes from messages and response."""
        try:
            # Manual extraction since we don't need the OpenAI module for this
            # Try to get the agent's current message history for prompts
            agent_messages = []
            if agent and hasattr(agent, "messages"):
                agent_messages = getattr(agent, "messages", [])
            elif agent and hasattr(agent, "conversation_history"):
                agent_messages = getattr(agent, "conversation_history", [])
            elif agent and hasattr(agent, "history"):
                agent_messages = getattr(agent, "history", [])

            # Also try to extract messages from the messages parameter itself
            if isinstance(messages, list):
                # If messages is a list of messages, use it directly
                agent_messages.extend(messages)
            elif isinstance(messages, dict) and "messages" in messages:
                # If messages contains a messages key
                agent_messages.extend(messages.get("messages", []))

            # Set prompt messages (input to LLM)
            prompt_index = 0
            for msg in agent_messages[-10:]:  # Get last 10 messages to avoid huge context
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")

                    # Handle different content formats
                    if content and isinstance(content, str) and content.strip():
                        safe_set_attribute(span, MessageAttributes.PROMPT_ROLE.format(i=prompt_index), role)
                        safe_set_attribute(
                            span, MessageAttributes.PROMPT_CONTENT.format(i=prompt_index), content[:2000]
                        )
                        prompt_index += 1
                    elif content and isinstance(content, list):
                        # Handle multi-modal content
                        content_str = str(content)[:2000]
                        safe_set_attribute(span, MessageAttributes.PROMPT_ROLE.format(i=prompt_index), role)
                        safe_set_attribute(span, MessageAttributes.PROMPT_CONTENT.format(i=prompt_index), content_str)
                        prompt_index += 1
                elif hasattr(msg, "content"):
                    # Handle object with content attribute
                    content = getattr(msg, "content", "")
                    role = getattr(msg, "role", "user")
                    if content and isinstance(content, str) and content.strip():
                        safe_set_attribute(span, MessageAttributes.PROMPT_ROLE.format(i=prompt_index), role)
                        safe_set_attribute(
                            span, MessageAttributes.PROMPT_CONTENT.format(i=prompt_index), str(content)[:2000]
                        )
                        prompt_index += 1

            # Set completion messages (response from LLM)
            completion_index = 0
            response_data = result if result else messages

            # Handle different response formats
            if isinstance(response_data, dict):
                choices = response_data.get("choices", [])
                for choice in choices:
                    message = choice.get("message", {})
                    role = message.get("role", "assistant")
                    content = message.get("content", "")

                    if content:
                        safe_set_attribute(span, MessageAttributes.COMPLETION_ROLE.format(i=completion_index), role)
                        safe_set_attribute(
                            span, MessageAttributes.COMPLETION_CONTENT.format(i=completion_index), content[:2000]
                        )

                    # Handle tool calls in the response
                    tool_calls = message.get("tool_calls", [])
                    for j, tool_call in enumerate(tool_calls):
                        tool_id = tool_call.get("id", "")
                        tool_name = tool_call.get("function", {}).get("name", "")
                        tool_args = tool_call.get("function", {}).get("arguments", "")

                        if tool_id:
                            safe_set_attribute(
                                span, MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=completion_index, j=j), tool_id
                            )
                        if tool_name:
                            safe_set_attribute(
                                span,
                                MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=completion_index, j=j),
                                tool_name,
                            )
                        if tool_args:
                            safe_set_attribute(
                                span,
                                MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=completion_index, j=j),
                                tool_args[:500],
                            )
                        safe_set_attribute(
                            span,
                            MessageAttributes.COMPLETION_TOOL_CALL_TYPE.format(i=completion_index, j=j),
                            "function",
                        )

                    completion_index += 1
            elif hasattr(response_data, "choices"):
                # Handle response object with choices attribute
                choices = getattr(response_data, "choices", [])
                for choice in choices:
                    message = getattr(choice, "message", None)
                    if message:
                        role = getattr(message, "role", "assistant")
                        content = getattr(message, "content", "")

                        if content:
                            safe_set_attribute(span, MessageAttributes.COMPLETION_ROLE.format(i=completion_index), role)
                            safe_set_attribute(
                                span,
                                MessageAttributes.COMPLETION_CONTENT.format(i=completion_index),
                                str(content)[:2000],
                            )

                        # Handle tool calls
                        tool_calls = getattr(message, "tool_calls", [])
                        for j, tool_call in enumerate(tool_calls):
                            tool_id = getattr(tool_call, "id", "")
                            function = getattr(tool_call, "function", None)
                            if function:
                                tool_name = getattr(function, "name", "")
                                tool_args = getattr(function, "arguments", "")

                                if tool_id:
                                    safe_set_attribute(
                                        span,
                                        MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=completion_index, j=j),
                                        tool_id,
                                    )
                                if tool_name:
                                    safe_set_attribute(
                                        span,
                                        MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=completion_index, j=j),
                                        tool_name,
                                    )
                                if tool_args:
                                    safe_set_attribute(
                                        span,
                                        MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(
                                            i=completion_index, j=j
                                        ),
                                        str(tool_args)[:500],
                                    )
                                safe_set_attribute(
                                    span,
                                    MessageAttributes.COMPLETION_TOOL_CALL_TYPE.format(i=completion_index, j=j),
                                    "function",
                                )

                        completion_index += 1

        except Exception as e:
            logger.error(f"Error extracting OpenAI message attributes: {e}")

    def _wrap_init_task(self, original_method):
        """Wrap init_task and add_task to create agent span hierarchy."""
        instrumentor = self

        def wrapper(self, execution=None, input=None, **kwargs):
            # Normalize parameters - handle both add_task(input=...) and init_task(execution=...)
            if execution is None and input is not None:
                # add_task call with input parameter - normalize to execution format
                if isinstance(input, str):
                    execution = {"input": {"text": input}}
                else:
                    execution = {"input": input}
            elif execution is None:
                # Neither execution nor input provided - create empty execution
                execution = {}

            # Extract session ID and agent info
            session_id = instrumentor._extract_session_id(execution)
            agent_name = getattr(self, "name", "unknown")
            agent_id = getattr(self, "id", "unknown")

            # Check if session already exists
            existing_session = instrumentor._context.get_session(session_id)
            if existing_session:
                # Session already exists, just continue
                # Call with original parameters
                if input is not None:
                    result = original_method(self, input=input, **kwargs)
                else:
                    result = original_method(self, execution)
                return result

            # Extract task input
            task_input = None
            if isinstance(execution, dict):
                if "input" in execution:
                    input_data = execution["input"]
                    if isinstance(input_data, dict) and "text" in input_data:
                        task_input = input_data["text"]
                    elif isinstance(input_data, str):
                        task_input = input_data

            # Create top-level conversation/session span - this is the ROOT span
            conversation_span_attributes = {
                SpanAttributes.AGENTOPS_ENTITY_NAME: f"Session - {agent_name}",
                "xpander.span.type": "session",
                "xpander.session.name": f"Session - {agent_name}",
                "xpander.agent.name": agent_name,
                "xpander.agent.id": agent_id,
                "xpander.session.id": session_id,
            }
            session_span, session_ctx, session_token = tracer.make_span(
                operation_name=f"session.{agent_name}",
                span_kind=SpanKind.AGENT,  # Use AGENT kind for the root session span
                attributes=conversation_span_attributes,
            )

            # Set task input on session span
            if task_input:
                safe_set_attribute(session_span, SpanAttributes.AGENTOPS_ENTITY_INPUT, task_input[:1000])
                safe_set_attribute(session_span, "xpander.session.initial_input", task_input[:500])

            # Create workflow span as child of session span (this will be the main execution span)
            trace.set_span_in_context(session_span)
            workflow_span_attributes = {
                "xpander.span.type": "workflow",
                "xpander.workflow.phase": "planning",
                "xpander.agent.name": agent_name,
                "xpander.agent.id": agent_id,
                "xpander.session.id": session_id,
                "agent.name": agent_name,
                "agent.id": agent_id,
            }
            workflow_span, workflow_ctx, workflow_token = tracer.make_span(
                operation_name=f"workflow.{agent_name}",
                span_kind=SpanKind.WORKFLOW,
                attributes=workflow_span_attributes,
            )

            # No separate agent span - workflow span contains all agent info

            # Initialize workflow state with persistent spans
            agent_info = {
                "agent_name": agent_name,
                "agent_id": agent_id,
                "task_input": task_input,
                "thread_id": execution.get("memory_thread_id") if isinstance(execution, dict) else None,
            }
            instrumentor._context.start_session(session_id, agent_info, workflow_span, None)  # No agent span
            # Store the session span as well
            instrumentor._context.start_conversation(session_id, session_span)

            try:
                # Execute original method - don't end agent span here, it will be ended in retrieve_execution_result
                # Call with original parameters
                if input is not None:
                    result = original_method(self, input=input, **kwargs)
                else:
                    result = original_method(self, execution)
                return result
            except Exception as e:
                # Use existing AgentOps error handling utilities
                _finish_span_error(workflow_span, e)
                raise

        return wrapper

    def _wrap_run_tools(self, original_method):
        """Wrap run_tools to create execution phase tool spans."""
        instrumentor = self

        def wrapper(self, tool_calls, payload_extension=None):
            session_id = instrumentor._get_session_id_from_agent(self)
            current_session = instrumentor._context.get_session(session_id)

            # Update workflow state
            step_num = (current_session.get("step_count", 0) + 1) if current_session else 1
            instrumentor._context.update_session(
                session_id,
                {
                    "step_count": step_num,
                    "phase": "executing",
                    "tools_executed": (current_session.get("tools_executed", []) if current_session else [])
                    + [instrumentor._extract_tool_name(tc) for tc in tool_calls],
                },
            )

            # Get current span context (should be the LLM span)
            current_span = trace.get_current_span()

            # Create execution phase span as child of current LLM span
            execution_span_context = trace.set_span_in_context(current_span) if current_span else None

            with instrumentor._tracer.start_as_current_span(
                "xpander.execution",
                kind=OTelSpanKind.INTERNAL,
                context=execution_span_context,
                attributes={
                    SpanAttributes.AGENTOPS_SPAN_KIND: SpanKind.TASK,
                    "xpander.span.type": "execution",
                    "xpander.workflow.phase": "executing",
                    "xpander.step.number": step_num,
                    "xpander.step.tool_count": len(tool_calls),
                    "xpander.session.id": session_id,
                },
            ) as execution_span:
                # Execute tools and create individual tool spans
                results = []
                conversation_finished = False

                for i, tool_call in enumerate(tool_calls):
                    tool_name = instrumentor._extract_tool_name(tool_call)
                    tool_params = instrumentor._extract_tool_params(tool_call)

                    # Check if this is the conversation finish tool
                    if tool_name == "xpfinish-agent-execution-finished":
                        conversation_finished = True

                    start_time = time.time()

                    # Create tool span as child of execution span
                    tool_span_context = trace.set_span_in_context(execution_span)

                    with instrumentor._tracer.start_as_current_span(
                        f"tool.{tool_name}",
                        kind=OTelSpanKind.CLIENT,
                        context=tool_span_context,
                        attributes={
                            SpanAttributes.AGENTOPS_SPAN_KIND: SpanKind.TOOL,
                            ToolAttributes.TOOL_NAME: tool_name,
                            ToolAttributes.TOOL_PARAMETERS: str(tool_params)[:500],
                            "xpander.span.type": "tool",
                            "xpander.workflow.phase": "executing",
                            "xpander.tool.step": step_num,
                            "xpander.tool.index": i,
                        },
                    ) as tool_span:
                        # Execute single tool
                        single_result = original_method(self, [tool_call], payload_extension)
                        results.extend(single_result)

                        # Record tool execution details
                        execution_time = time.time() - start_time
                        safe_set_attribute(tool_span, "xpander.tool.execution_time", execution_time)

                        # Add tool result if available
                        if single_result:
                            result_summary = f"Executed successfully with {len(single_result)} results"
                            safe_set_attribute(tool_span, "xpander.tool.result_summary", result_summary)

                            # Store actual result data using existing AgentOps utilities
                            try:
                                result_content = ""

                                for i, result_item in enumerate(single_result):
                                    # Handle xpander_sdk.ToolCallResult objects specifically
                                    if hasattr(result_item, "__class__") and "ToolCallResult" in str(type(result_item)):
                                        # Extract the actual result content from ToolCallResult
                                        try:
                                            if hasattr(result_item, "result") and result_item.result is not None:
                                                actual_result = result_item.result
                                                if isinstance(actual_result, str):
                                                    result_content += actual_result[:1000] + "\n"
                                                else:
                                                    result_content += safe_serialize(actual_result)[:1000] + "\n"
                                            elif hasattr(result_item, "data") and result_item.data is not None:
                                                result_content += safe_serialize(result_item.data)[:1000] + "\n"
                                            else:
                                                # Fallback: try to find any content attribute
                                                for attr_name in ["content", "output", "value", "response"]:
                                                    if hasattr(result_item, attr_name):
                                                        attr_value = getattr(result_item, attr_name)
                                                        if attr_value is not None:
                                                            result_content += safe_serialize(attr_value)[:1000] + "\n"
                                                            break
                                                else:
                                                    # If no content attributes found, indicate this
                                                    result_content += "ToolCallResult object (no extractable content)\n"
                                        except Exception as attr_e:
                                            logger.debug(f"Error extracting from ToolCallResult: {attr_e}")
                                            result_content += "ToolCallResult object (extraction failed)\n"

                                    # Handle regular objects and primitives
                                    elif isinstance(result_item, (str, int, float, bool)):
                                        result_content += str(result_item)[:1000] + "\n"
                                    elif hasattr(result_item, "__dict__"):
                                        # Convert objects to dict using existing utility
                                        result_dict = model_to_dict(result_item)
                                        result_content += safe_serialize(result_dict)[:1000] + "\n"
                                    else:
                                        # Use safe_serialize for consistent conversion
                                        result_content += safe_serialize(result_item)[:1000] + "\n"

                                if result_content.strip():
                                    final_content = result_content.strip()[:2000]
                                    safe_set_attribute(tool_span, ToolAttributes.TOOL_RESULT, final_content)
                                else:
                                    safe_set_attribute(
                                        tool_span, ToolAttributes.TOOL_RESULT, "No extractable content found"
                                    )

                            except Exception as e:
                                logger.error(f"Error setting tool result: {e}")
                                safe_set_attribute(
                                    tool_span, ToolAttributes.TOOL_RESULT, f"Error capturing result: {e}"
                                )
                        else:
                            safe_set_attribute(tool_span, "xpander.tool.result_summary", "No results returned")

                # If conversation is finished, mark for session closure
                if conversation_finished:
                    # Since session span is now the conversation span, we need to close all spans
                    # when the conversation finishes
                    pass  # Session closure will be handled in retrieve_execution_result

                return results

        return wrapper

    def _wrap_add_messages(self, original_method):
        """Wrap add_messages to create LLM spans with proper parent-child relationship."""
        instrumentor = self

        def wrapper(self, messages):
            session_id = instrumentor._get_session_id_from_agent(self)
            current_session = instrumentor._context.get_session(session_id)
            current_phase = instrumentor._context.get_workflow_phase(session_id)
            workflow_span = instrumentor._context.get_workflow_span(session_id)

            # Create LLM span as child of workflow span (not conversation span)
            # The hierarchy should be: session -> agent/workflow -> LLM -> execution -> tools
            llm_span_context = trace.set_span_in_context(workflow_span) if workflow_span else None

            # Call original method first to get the actual OpenAI response
            result = original_method(self, messages)

            # Now create a span that captures the LLM interaction with the actual response data
            with instrumentor._tracer.start_as_current_span(
                f"llm.{current_phase}",
                kind=OTelSpanKind.CLIENT,
                context=llm_span_context,
                attributes={
                    SpanAttributes.AGENTOPS_SPAN_KIND: SpanKind.LLM,
                    "xpander.span.type": "llm",
                    "xpander.workflow.phase": current_phase,
                    "xpander.session.id": session_id,
                },
            ) as llm_span:
                # Extract and set OpenAI message data from the messages and response
                instrumentor._extract_and_set_openai_message_attributes(llm_span, messages, result, self)

                # Extract and set LLM metadata from the result if possible
                llm_data = instrumentor._extract_llm_data_from_messages(result if result else messages)
                if llm_data:
                    if "model" in llm_data:
                        safe_set_attribute(llm_span, SpanAttributes.LLM_REQUEST_MODEL, llm_data["model"])
                        safe_set_attribute(llm_span, SpanAttributes.LLM_RESPONSE_MODEL, llm_data["model"])

                    if "usage" in llm_data:
                        usage = llm_data["usage"]
                        if "prompt_tokens" in usage:
                            safe_set_attribute(llm_span, SpanAttributes.LLM_USAGE_PROMPT_TOKENS, usage["prompt_tokens"])
                        if "completion_tokens" in usage:
                            safe_set_attribute(
                                llm_span, SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, usage["completion_tokens"]
                            )
                        if "total_tokens" in usage:
                            safe_set_attribute(llm_span, SpanAttributes.LLM_USAGE_TOTAL_TOKENS, usage["total_tokens"])
                            # Update workflow state
                            instrumentor._context.update_session(
                                session_id,
                                {
                                    "total_tokens": (current_session.get("total_tokens", 0) if current_session else 0)
                                    + usage["total_tokens"]
                                },
                            )

            return result

        return wrapper

    def _wrap_is_finished(self, original_method):
        """Wrap is_finished to track workflow completion."""
        instrumentor = self

        def wrapper(self):
            result = original_method(self)

            if result:
                session_id = instrumentor._get_session_id_from_agent(self)

                # Update session to finished state
                instrumentor._context.update_session(session_id, {"phase": "finished", "end_time": time.time()})

            return result

        return wrapper

    def _wrap_extract_tool_calls(self, original_method):
        """Wrap extract_tool_calls to track tool planning."""

        def wrapper(self, messages):
            result = original_method(self, messages)
            return result

        return wrapper

    def _wrap_report_execution_metrics(self, original_method):
        """Wrap report_execution_metrics to track metrics."""

        def wrapper(self, llm_tokens=None, ai_model=None):
            result = original_method(self, llm_tokens, ai_model)
            return result

        return wrapper

    def _wrap_retrieve_execution_result(self, original_method):
        """Wrap retrieve_execution_result to finalize agent and workflow spans."""
        instrumentor = self

        def wrapper(self):
            session_id = instrumentor._get_session_id_from_agent(self)
            current_session = instrumentor._context.get_session(session_id)
            workflow_span = instrumentor._context.get_workflow_span(session_id)
            session_span = instrumentor._context.get_conversation_span(session_id)  # This is now the root session span

            try:
                # Execute and capture result
                result = original_method(self)

                # Add workflow summary to the persistent workflow span
                if workflow_span and current_session:
                    safe_set_attribute(
                        workflow_span, "xpander.workflow.total_steps", current_session.get("step_count", 0)
                    )
                    safe_set_attribute(
                        workflow_span, "xpander.workflow.total_tokens", current_session.get("total_tokens", 0)
                    )
                    safe_set_attribute(
                        workflow_span, "xpander.workflow.tools_used", len(current_session.get("tools_executed", []))
                    )

                    # Calculate total execution time
                    start_time = current_session.get("start_time", time.time())
                    execution_time = time.time() - start_time
                    safe_set_attribute(workflow_span, "xpander.workflow.execution_time", execution_time)
                    safe_set_attribute(workflow_span, "xpander.workflow.phase", "completed")

                # Set result details on session and workflow spans
                if result:
                    result_content = ""
                    if hasattr(result, "result"):
                        result_content = str(result.result)[:1000]

                    # Set on session span (root span)
                    if session_span and result_content:
                        safe_set_attribute(session_span, SpanAttributes.AGENTOPS_ENTITY_OUTPUT, result_content)
                        safe_set_attribute(session_span, "xpander.session.final_result", result_content)
                        if hasattr(result, "memory_thread_id"):
                            safe_set_attribute(session_span, "xpander.session.thread_id", result.memory_thread_id)

                    if workflow_span:
                        if result_content:
                            safe_set_attribute(workflow_span, "xpander.result.content", result_content)
                        if hasattr(result, "memory_thread_id"):
                            safe_set_attribute(workflow_span, "xpander.result.thread_id", result.memory_thread_id)

                # Add session summary to session span
                if session_span and current_session:
                    safe_set_attribute(
                        session_span, "xpander.session.total_steps", current_session.get("step_count", 0)
                    )
                    safe_set_attribute(
                        session_span, "xpander.session.total_tokens", current_session.get("total_tokens", 0)
                    )
                    safe_set_attribute(
                        session_span, "xpander.session.tools_used", len(current_session.get("tools_executed", []))
                    )

                    start_time = current_session.get("start_time", time.time())
                    execution_time = time.time() - start_time
                    safe_set_attribute(session_span, "xpander.session.execution_time", execution_time)

                # Close all spans - session span should be closed last
                if workflow_span:
                    _finish_span_success(workflow_span)
                    workflow_span.end()

                if session_span:
                    _finish_span_success(session_span)
                    session_span.end()

                return result

            except Exception as e:
                # Mark spans as failed and close them in proper order
                if workflow_span:
                    _finish_span_error(workflow_span, e)
                    workflow_span.end()

                if session_span:
                    _finish_span_error(session_span, e)
                    session_span.end()
                raise
            finally:
                # Clean up session
                instrumentor._context.end_session(session_id)

        return wrapper

    def _instrument(self, **kwargs):
        """Instrument the Xpander SDK."""
        try:
            # Import xpander modules
            from xpander_sdk import Agent

            # Set up tracing using existing AgentOps tracer
            self._tracer = tracer.get_tracer()
            # Attribute manager already initialized in __init__

            # Wrap Agent methods
            Agent.add_task = self._wrap_init_task(Agent.add_task)
            Agent.init_task = self._wrap_init_task(Agent.init_task)  # Also wrap init_task for completeness
            Agent.run_tools = self._wrap_run_tools(Agent.run_tools)
            Agent.add_messages = self._wrap_add_messages(Agent.add_messages)
            Agent.is_finished = self._wrap_is_finished(Agent.is_finished)
            Agent.extract_tool_calls = self._wrap_extract_tool_calls(Agent.extract_tool_calls)
            Agent.report_execution_metrics = self._wrap_report_execution_metrics(Agent.report_execution_metrics)
            Agent.retrieve_execution_result = self._wrap_retrieve_execution_result(Agent.retrieve_execution_result)

        except ImportError:
            logger.debug("Xpander SDK not available")
        except Exception as e:
            logger.error(f"Failed to instrument Xpander SDK: {e}")

    def _uninstrument(self, **kwargs):
        """Uninstrument the Xpander SDK."""
        pass

    def _create_metrics(self, meter: Meter) -> StandardMetrics:
        """Create metrics for Xpander instrumentation."""
        return StandardMetrics(
            requests_active=meter.create_up_down_counter(
                name="xpander_requests_active",
                description="Number of active Xpander requests",
            ),
            requests_duration=meter.create_histogram(
                name="xpander_requests_duration",
                description="Duration of Xpander requests",
                unit="s",
            ),
            requests_total=meter.create_counter(
                name="xpander_requests_total",
                description="Total number of Xpander requests",
            ),
            requests_error=meter.create_counter(
                name="xpander_requests_error",
                description="Number of Xpander request errors",
            ),
        )
