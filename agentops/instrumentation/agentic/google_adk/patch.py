"""Patch functions for Google ADK instrumentation.

This module patches key methods in Google ADK to:
1. Prevent ADK from creating its own spans
2. Create AgentOps spans that mirror ADK's telemetry
3. Extract and set proper attributes on spans
"""

import json
import wrapt
from typing import Any
from opentelemetry import trace as opentelemetry_api_trace
from opentelemetry.trace import SpanKind as SpanKind

from agentops.logging import logger
from agentops.semconv import SpanAttributes, ToolAttributes, MessageAttributes, AgentAttributes


_wrapped_methods = []


class NoOpSpan:
    """A no-op span that does nothing."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def set_attribute(self, *args, **kwargs):
        pass

    def set_attributes(self, *args, **kwargs):
        pass

    def add_event(self, *args, **kwargs):
        pass

    def set_status(self, *args, **kwargs):
        pass

    def update_name(self, *args, **kwargs):
        pass

    def is_recording(self):
        return False

    def end(self, *args, **kwargs):
        pass

    def record_exception(self, *args, **kwargs):
        pass


class NoOpTracer:
    """A tracer that creates no-op spans to prevent ADK from creating real spans."""

    def start_as_current_span(self, *args, **kwargs):
        """Return a no-op context manager."""
        return NoOpSpan()

    def start_span(self, *args, **kwargs):
        """Return a no-op span."""
        return NoOpSpan()

    def use_span(self, *args, **kwargs):
        """Return a no-op context manager."""
        return NoOpSpan()


def _build_llm_request_for_trace(llm_request) -> dict:
    """Build a dictionary representation of the LLM request for tracing."""
    from google.genai import types

    result = {
        "model": llm_request.model,
        "config": llm_request.config.model_dump(exclude_none=True, exclude="response_schema"),
        "contents": [],
    }

    for content in llm_request.contents:
        parts = [part for part in content.parts if not hasattr(part, "inline_data") or not part.inline_data]
        result["contents"].append(types.Content(role=content.role, parts=parts).model_dump(exclude_none=True))
    return result


def _extract_messages_from_contents(contents: list) -> dict:
    """Extract messages from LLM contents for proper indexing."""
    attributes = {}

    for i, content in enumerate(contents):
        # Get role and normalize it
        raw_role = content.get("role", "user")

        # Hardcode role mapping for consistency
        if raw_role == "model":
            role = "assistant"
        elif raw_role == "user":
            role = "user"
        elif raw_role == "system":
            role = "system"
        else:
            role = raw_role  # Keep original if not recognized

        parts = content.get("parts", [])

        # Set role
        attributes[MessageAttributes.PROMPT_ROLE.format(i=i)] = role

        # Extract content from parts
        text_parts = []
        for part in parts:
            if "text" in part and part.get("text") is not None:
                text_parts.append(str(part["text"]))
            elif "function_call" in part:
                # Function calls in prompts are typically from the model's previous responses
                func_call = part["function_call"]
                # Store as a generic attribute since MessageAttributes doesn't have prompt tool calls
                attributes[f"gen_ai.prompt.{i}.function_call.name"] = func_call.get("name", "")
                attributes[f"gen_ai.prompt.{i}.function_call.args"] = json.dumps(func_call.get("args", {}))
                if "id" in func_call:
                    attributes[f"gen_ai.prompt.{i}.function_call.id"] = func_call["id"]
            elif "function_response" in part:
                # Function responses are typically user messages with tool results
                func_resp = part["function_response"]
                attributes[f"gen_ai.prompt.{i}.function_response.name"] = func_resp.get("name", "")
                attributes[f"gen_ai.prompt.{i}.function_response.result"] = json.dumps(func_resp.get("response", {}))
                if "id" in func_resp:
                    attributes[f"gen_ai.prompt.{i}.function_response.id"] = func_resp["id"]

        # Combine text parts
        if text_parts:
            attributes[MessageAttributes.PROMPT_CONTENT.format(i=i)] = "\n".join(text_parts)

    return attributes


def _extract_llm_attributes(llm_request_dict: dict, llm_response: Any) -> dict:
    """Extract attributes from LLM request and response."""
    attributes = {}

    # Model
    if "model" in llm_request_dict:
        attributes[SpanAttributes.LLM_REQUEST_MODEL] = llm_request_dict["model"]

    # Config
    if "config" in llm_request_dict:
        config = llm_request_dict["config"]

        # System instruction - commented out, now handled as a system role message
        # if "system_instruction" in config:
        #     attributes[SpanAttributes.LLM_REQUEST_SYSTEM_INSTRUCTION] = config["system_instruction"]

        # Temperature
        if "temperature" in config:
            attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = config["temperature"]

        # Max output tokens
        if "max_output_tokens" in config:
            attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = config["max_output_tokens"]

        # Top P
        if "top_p" in config:
            attributes[SpanAttributes.LLM_REQUEST_TOP_P] = config["top_p"]

        # Top K
        if "top_k" in config:
            attributes[SpanAttributes.LLM_REQUEST_TOP_K] = config["top_k"]

        # Candidate count
        if "candidate_count" in config:
            attributes[SpanAttributes.LLM_REQUEST_CANDIDATE_COUNT] = config["candidate_count"]

        # Stop sequences
        if "stop_sequences" in config:
            attributes[SpanAttributes.LLM_REQUEST_STOP_SEQUENCES] = json.dumps(config["stop_sequences"])

        # Response MIME type
        if "response_mime_type" in config:
            attributes["gen_ai.request.response_mime_type"] = config["response_mime_type"]

        # Tools/Functions
        if "tools" in config:
            # Extract tool definitions
            for i, tool in enumerate(config["tools"]):
                if "function_declarations" in tool:
                    for j, func in enumerate(tool["function_declarations"]):
                        attributes[f"gen_ai.request.tools.{j}.name"] = func.get("name", "")
                        attributes[f"gen_ai.request.tools.{j}.description"] = func.get("description", "")

    # Messages - handle system instruction and regular contents
    message_index = 0

    # First, add system instruction as a system role message if present
    # TODO: This is not Chat Completions format but doing this for frontend rendering consistency
    if "config" in llm_request_dict and "system_instruction" in llm_request_dict["config"]:
        system_instruction = llm_request_dict["config"]["system_instruction"]
        attributes[MessageAttributes.PROMPT_ROLE.format(i=message_index)] = "system"
        attributes[MessageAttributes.PROMPT_CONTENT.format(i=message_index)] = system_instruction
        message_index += 1

    # Then add regular contents with proper indexing
    if "contents" in llm_request_dict:
        for content in llm_request_dict["contents"]:
            # Get role and normalize it
            raw_role = content.get("role", "user")

            # Hardcode role mapping for consistency
            if raw_role == "model":
                role = "assistant"
            elif raw_role == "user":
                role = "user"
            elif raw_role == "system":
                role = "system"
            else:
                role = raw_role  # Keep original if not recognized

            parts = content.get("parts", [])

            # Set role
            attributes[MessageAttributes.PROMPT_ROLE.format(i=message_index)] = role

            # Extract content from parts
            text_parts = []
            for part in parts:
                if "text" in part and part.get("text") is not None:
                    text_parts.append(str(part["text"]))
                elif "function_call" in part:
                    # Function calls in prompts are typically from the model's previous responses
                    func_call = part["function_call"]
                    # Store as a generic attribute since MessageAttributes doesn't have prompt tool calls
                    attributes[f"gen_ai.prompt.{message_index}.function_call.name"] = func_call.get("name", "")
                    attributes[f"gen_ai.prompt.{message_index}.function_call.args"] = json.dumps(
                        func_call.get("args", {})
                    )
                    if "id" in func_call:
                        attributes[f"gen_ai.prompt.{message_index}.function_call.id"] = func_call["id"]
                elif "function_response" in part:
                    # Function responses are typically user messages with tool results
                    func_resp = part["function_response"]
                    attributes[f"gen_ai.prompt.{message_index}.function_response.name"] = func_resp.get("name", "")
                    attributes[f"gen_ai.prompt.{message_index}.function_response.result"] = json.dumps(
                        func_resp.get("response", {})
                    )
                    if "id" in func_resp:
                        attributes[f"gen_ai.prompt.{message_index}.function_response.id"] = func_resp["id"]

            # Combine text parts
            if text_parts:
                attributes[MessageAttributes.PROMPT_CONTENT.format(i=message_index)] = "\n".join(text_parts)

            message_index += 1

    # Response
    if llm_response:
        try:
            response_dict = json.loads(llm_response) if isinstance(llm_response, str) else llm_response

            # Response model
            if "model" in response_dict:
                attributes[SpanAttributes.LLM_RESPONSE_MODEL] = response_dict["model"]

            # Usage metadata
            if "usage_metadata" in response_dict:
                usage = response_dict["usage_metadata"]
                if "prompt_token_count" in usage:
                    attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["prompt_token_count"]
                if "candidates_token_count" in usage:
                    attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["candidates_token_count"]
                if "total_token_count" in usage:
                    attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_token_count"]

                # Additional token details if available
                if "prompt_tokens_details" in usage:
                    for detail in usage["prompt_tokens_details"]:
                        if "modality" in detail and "token_count" in detail:
                            attributes[f"gen_ai.usage.prompt_tokens.{detail['modality'].lower()}"] = detail[
                                "token_count"
                            ]

                if "candidates_tokens_details" in usage:
                    for detail in usage["candidates_tokens_details"]:
                        if "modality" in detail and "token_count" in detail:
                            attributes[f"gen_ai.usage.completion_tokens.{detail['modality'].lower()}"] = detail[
                                "token_count"
                            ]

            # Response content
            if "content" in response_dict and "parts" in response_dict["content"]:
                parts = response_dict["content"]["parts"]

                # Set completion role and content - hardcode role as 'assistant' for consistency
                attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] = "assistant"

                text_parts = []
                tool_call_index = 0
                for part in parts:
                    if "text" in part and part.get("text") is not None:
                        text_parts.append(str(part["text"]))
                    elif "function_call" in part:
                        # This is a function call in the response
                        func_call = part["function_call"]
                        attributes[MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=tool_call_index)] = (
                            func_call.get("name", "")
                        )
                        attributes[MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=0, j=tool_call_index)] = (
                            json.dumps(func_call.get("args", {}))
                        )
                        if "id" in func_call:
                            attributes[MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=0, j=tool_call_index)] = (
                                func_call["id"]
                            )
                        tool_call_index += 1

                if text_parts:
                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = "\n".join(text_parts)

            # Finish reason
            if "finish_reason" in response_dict:
                attributes[SpanAttributes.LLM_RESPONSE_FINISH_REASON] = response_dict["finish_reason"]

            # Response ID
            if "id" in response_dict:
                attributes[SpanAttributes.LLM_RESPONSE_ID] = response_dict["id"]

        except Exception as e:
            logger.debug(f"Failed to extract response attributes: {e}")

    return attributes


# Wrapper for Runner.run_async - REMOVED per user request
# We just pass through without creating a span
def _runner_run_async_wrapper(agentops_tracer):
    def actual_decorator(wrapped, instance, args, kwargs):
        async def new_function():
            # Just pass through without creating a span
            async_gen = wrapped(*args, **kwargs)
            async for item in async_gen:
                yield item

        return new_function()

    return actual_decorator


def extract_agent_attributes(instance):
    attributes = {}
    # Use AgentAttributes from semconv
    attributes[AgentAttributes.AGENT_NAME] = instance.name
    if hasattr(instance, "description"):
        attributes["agent.description"] = instance.description
    if hasattr(instance, "model"):
        attributes["agent.model"] = instance.model
    if hasattr(instance, "instruction"):
        attributes["agent.instruction"] = instance.instruction
    if hasattr(instance, "tools"):
        for tool in instance.tools:
            if hasattr(tool, "name"):
                attributes[ToolAttributes.TOOL_NAME] = tool.name
            if hasattr(tool, "description"):
                attributes[ToolAttributes.TOOL_DESCRIPTION] = tool.description
    if hasattr(instance, "output_key"):
        attributes["agent.output_key"] = instance.output_key
    # Subagents
    if hasattr(instance, "sub_agents"):
        # recursively extract attributes from subagents but add a prefix to the keys, also with indexing, because we can have multiple subagents, also subagent can have subagents, So have to index them even if they are not in the same level
        for i, sub_agent in enumerate(instance.sub_agents):
            sub_agent_attributes = extract_agent_attributes(sub_agent)
            for key, value in sub_agent_attributes.items():
                attributes[f"agent.sub_agents.{i}.{key}"] = value
    return attributes


# Wrapper for BaseAgent.run_async
def _base_agent_run_async_wrapper(agentops_tracer):
    def actual_decorator(wrapped, instance, args, kwargs):
        async def new_function():
            agent_name = instance.name if hasattr(instance, "name") else "unknown"
            span_name = f"adk.agent.{agent_name}"

            with agentops_tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT) as span:
                span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, "agent")
                span.set_attribute(SpanAttributes.LLM_SYSTEM, "gcp.vertex.agent")
                span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")

                span.set_attributes(extract_agent_attributes(instance))
                # # Extract invocation context if available
                if len(args) > 0 and hasattr(args[0], "invocation_id"):
                    span.set_attribute("adk.invocation_id", args[0].invocation_id)

                async_gen = wrapped(*args, **kwargs)
                async for item in async_gen:
                    yield item

        return new_function()

    return actual_decorator


# Wrapper for BaseLlmFlow._call_llm_async
def _base_llm_flow_call_llm_async_wrapper(agentops_tracer):
    def actual_decorator(wrapped, instance, args, kwargs):
        async def new_function():
            # Extract model info and llm_request if available
            model_name = "unknown"
            llm_request = None

            if len(args) > 1:
                llm_request = args[1]
                if hasattr(llm_request, "model"):
                    model_name = llm_request.model

            span_name = f"adk.llm.{model_name}"

            with agentops_tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT) as span:
                span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, "request")
                span.set_attribute(SpanAttributes.LLM_SYSTEM, "gcp.vertex.agent")
                span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "request")

                # Extract and set attributes from llm_request before the call
                if llm_request:
                    llm_request_dict = _build_llm_request_for_trace(llm_request)
                    # Only extract request attributes here, response will be set later by _finalize_model_response_event
                    llm_attrs = _extract_llm_attributes(llm_request_dict, None)
                    for key, value in llm_attrs.items():
                        span.set_attribute(key, value)

                # Note: The actual LLM response attributes will be set by
                # _finalize_model_response_event_wrapper when ADK finalizes the response

                async_gen = wrapped(*args, **kwargs)
                async for item in async_gen:
                    yield item

        return new_function()

    return actual_decorator


# Wrapper for ADK telemetry functions - these add attributes to current span
def _adk_trace_tool_call_wrapper(agentops_tracer):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        # Call original to preserve ADK behavior
        result = wrapped(*args, **kwargs)

        tool_args = args[0] if args else kwargs.get("args")
        current_span = opentelemetry_api_trace.get_current_span()
        if current_span.is_recording() and tool_args is not None:
            current_span.set_attribute(SpanAttributes.LLM_SYSTEM, "gcp.vertex.agent")
            current_span.set_attribute("gcp.vertex.agent.tool_call_args", json.dumps(tool_args))
        return result

    return wrapper


def _adk_trace_tool_response_wrapper(agentops_tracer):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        # Call original to preserve ADK behavior
        result = wrapped(*args, **kwargs)

        invocation_context = args[0] if len(args) > 0 else kwargs.get("invocation_context")
        event_id = args[1] if len(args) > 1 else kwargs.get("event_id")
        function_response_event = args[2] if len(args) > 2 else kwargs.get("function_response_event")

        current_span = opentelemetry_api_trace.get_current_span()
        if current_span.is_recording():
            current_span.set_attribute(SpanAttributes.LLM_SYSTEM, "gcp.vertex.agent")
            if invocation_context:
                current_span.set_attribute("gcp.vertex.agent.invocation_id", invocation_context.invocation_id)
            if event_id:
                current_span.set_attribute("gcp.vertex.agent.event_id", event_id)
            if function_response_event:
                current_span.set_attribute(
                    "gcp.vertex.agent.tool_response", function_response_event.model_dump_json(exclude_none=True)
                )
            current_span.set_attribute("gcp.vertex.agent.llm_request", "{}")
            current_span.set_attribute("gcp.vertex.agent.llm_response", "{}")
        return result

    return wrapper


def _adk_trace_call_llm_wrapper(agentops_tracer):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        # Call the original first to ensure ADK's behavior is preserved
        result = wrapped(*args, **kwargs)

        invocation_context = args[0] if len(args) > 0 else kwargs.get("invocation_context")
        event_id = args[1] if len(args) > 1 else kwargs.get("event_id")
        llm_request = args[2] if len(args) > 2 else kwargs.get("llm_request")
        llm_response = args[3] if len(args) > 3 else kwargs.get("llm_response")

        current_span = opentelemetry_api_trace.get_current_span()
        if current_span.is_recording():
            current_span.set_attribute(SpanAttributes.LLM_SYSTEM, "gcp.vertex.agent")
            if llm_request:
                current_span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, llm_request.model)
            if invocation_context:
                current_span.set_attribute("gcp.vertex.agent.invocation_id", invocation_context.invocation_id)
                current_span.set_attribute("gcp.vertex.agent.session_id", invocation_context.session.id)
            if event_id:
                current_span.set_attribute("gcp.vertex.agent.event_id", event_id)

            if llm_request:
                llm_request_dict = _build_llm_request_for_trace(llm_request)
                current_span.set_attribute("gcp.vertex.agent.llm_request", json.dumps(llm_request_dict))

                # Extract and set all attributes including usage
                llm_response_json = None
                if llm_response:
                    llm_response_json = llm_response.model_dump_json(exclude_none=True)
                    current_span.set_attribute("gcp.vertex.agent.llm_response", llm_response_json)

                llm_attrs = _extract_llm_attributes(llm_request_dict, llm_response_json)
                for key, value in llm_attrs.items():
                    current_span.set_attribute(key, value)

        return result

    return wrapper


def _adk_trace_send_data_wrapper(agentops_tracer):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        # Call original to preserve ADK behavior
        result = wrapped(*args, **kwargs)

        invocation_context = args[0] if len(args) > 0 else kwargs.get("invocation_context")
        event_id = args[1] if len(args) > 1 else kwargs.get("event_id")
        data = args[2] if len(args) > 2 else kwargs.get("data")

        current_span = opentelemetry_api_trace.get_current_span()
        if current_span.is_recording():
            if invocation_context:
                current_span.set_attribute("gcp.vertex.agent.invocation_id", invocation_context.invocation_id)
            if event_id:
                current_span.set_attribute("gcp.vertex.agent.event_id", event_id)
            if data:
                from google.genai import types

                current_span.set_attribute(
                    "gcp.vertex.agent.data",
                    json.dumps(
                        [
                            types.Content(role=content.role, parts=content.parts).model_dump(exclude_none=True)
                            for content in data
                        ]
                    ),
                )
        return result

    return wrapper


# Wrapper for _finalize_model_response_event to capture response attributes
def _finalize_model_response_event_wrapper(agentops_tracer):
    def actual_decorator(wrapped, instance, args, kwargs):
        # Call the original method
        result = wrapped(*args, **kwargs)

        # Extract llm_request and llm_response from args
        llm_request = args[0] if len(args) > 0 else kwargs.get("llm_request")
        llm_response = args[1] if len(args) > 1 else kwargs.get("llm_response")

        # Get the current span and set response attributes
        current_span = opentelemetry_api_trace.get_current_span()
        if current_span.is_recording() and llm_request and llm_response:
            span_name = getattr(current_span, "name", "")
            if "adk.llm" in span_name:
                # Build request dict
                llm_request_dict = _build_llm_request_for_trace(llm_request)

                # Extract response attributes
                llm_response_json = llm_response.model_dump_json(exclude_none=True)
                llm_attrs = _extract_llm_attributes(llm_request_dict, llm_response_json)

                # Only set response-related attributes (request attrs already set)
                for key, value in llm_attrs.items():
                    if "usage" in key or "completion" in key or "response" in key:
                        current_span.set_attribute(key, value)

        return result

    return actual_decorator


# Wrapper for tool execution that creates a single merged span
def _call_tool_async_wrapper(agentops_tracer):
    """Wrapper that creates a single span for tool call and response."""

    def actual_decorator(wrapped, instance, args, kwargs):
        async def new_function():
            # Extract tool info from args
            tool = args[0] if args else kwargs.get("tool")
            tool_args = args[1] if len(args) > 1 else kwargs.get("args", {})
            tool_context = args[2] if len(args) > 2 else kwargs.get("tool_context")

            tool_name = getattr(tool, "name", "unknown_tool")
            span_name = f"adk.tool.{tool_name}"

            with agentops_tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT) as span:
                span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, "tool")
                span.set_attribute(SpanAttributes.LLM_SYSTEM, "gcp.vertex.agent")
                span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "tool")

                # Set tool call attributes
                span.set_attribute(ToolAttributes.TOOL_NAME, tool_name)
                if hasattr(tool, "description"):
                    span.set_attribute(ToolAttributes.TOOL_DESCRIPTION, tool.description)
                if hasattr(tool, "is_long_running"):
                    span.set_attribute("tool.is_long_running", tool.is_long_running)
                span.set_attribute(ToolAttributes.TOOL_PARAMETERS, json.dumps(tool_args))

                if tool_context and hasattr(tool_context, "function_call_id"):
                    span.set_attribute("tool.call_id", tool_context.function_call_id)
                if tool_context and hasattr(tool_context, "invocation_context"):
                    span.set_attribute("adk.invocation_id", tool_context.invocation_context.invocation_id)

                # Execute the tool
                result = await wrapped(*args, **kwargs)

                # Set tool response attributes
                if result:
                    if isinstance(result, dict):
                        span.set_attribute(ToolAttributes.TOOL_RESULT, json.dumps(result))
                    else:
                        span.set_attribute(ToolAttributes.TOOL_RESULT, str(result))

                return result

        return new_function()

    return actual_decorator


def _patch(module_name: str, object_name: str, method_name: str, wrapper_function, agentops_tracer):
    """Helper to apply a patch and keep track of it."""
    try:
        module = __import__(module_name, fromlist=[object_name])
        obj = getattr(module, object_name)
        wrapt.wrap_function_wrapper(obj, method_name, wrapper_function(agentops_tracer))
        _wrapped_methods.append((obj, method_name))
        logger.debug(f"Successfully wrapped {module_name}.{object_name}.{method_name}")
    except Exception as e:
        logger.warning(f"Could not wrap {module_name}.{object_name}.{method_name}: {e}")


def _patch_module_function(module_name: str, function_name: str, wrapper_function, agentops_tracer):
    """Helper to patch module-level functions."""
    try:
        module = __import__(module_name, fromlist=[function_name])
        wrapt.wrap_function_wrapper(module, function_name, wrapper_function(agentops_tracer))
        _wrapped_methods.append((module, function_name))
        logger.debug(f"Successfully wrapped {module_name}.{function_name}")
    except Exception as e:
        logger.warning(f"Could not wrap {module_name}.{function_name}: {e}")


def patch_adk(agentops_tracer):
    """Apply all patches to Google ADK modules."""
    logger.debug("Applying Google ADK patches for AgentOps instrumentation")

    # First, disable ADK's own tracer by replacing it with our NoOpTracer
    noop_tracer = NoOpTracer()
    try:
        import google.adk.telemetry as adk_telemetry

        # Replace the tracer with our no-op version
        adk_telemetry.tracer = noop_tracer
        logger.debug("Replaced ADK's tracer with NoOpTracer")
    except Exception as e:
        logger.warning(f"Failed to replace ADK tracer: {e}")

    # Also replace the tracer in all modules that have already imported it
    modules_to_patch = [
        "google.adk.runners",
        "google.adk.agents.base_agent",
        "google.adk.flows.llm_flows.base_llm_flow",
        "google.adk.flows.llm_flows.functions",
    ]

    import sys

    for module_name in modules_to_patch:
        if module_name in sys.modules:
            try:
                module = sys.modules[module_name]
                if hasattr(module, "tracer"):
                    module.tracer = noop_tracer
                    logger.debug(f"Replaced tracer in {module_name}")
            except Exception as e:
                logger.warning(f"Failed to replace tracer in {module_name}: {e}")

    # Patch methods that create top-level AgentOps spans
    # Skip runner patching - we don't want adk.runner spans
    _patch("google.adk.agents.base_agent", "BaseAgent", "run_async", _base_agent_run_async_wrapper, agentops_tracer)

    # Patch ADK's telemetry functions to add attributes to AgentOps spans
    _patch_module_function("google.adk.telemetry", "trace_tool_call", _adk_trace_tool_call_wrapper, agentops_tracer)
    _patch_module_function(
        "google.adk.telemetry", "trace_tool_response", _adk_trace_tool_response_wrapper, agentops_tracer
    )
    _patch_module_function("google.adk.telemetry", "trace_call_llm", _adk_trace_call_llm_wrapper, agentops_tracer)

    _patch_module_function("google.adk.telemetry", "trace_send_data", _adk_trace_send_data_wrapper, agentops_tracer)

    # Patch method that creates nested spans
    _patch(
        "google.adk.flows.llm_flows.base_llm_flow",
        "BaseLlmFlow",
        "_call_llm_async",
        _base_llm_flow_call_llm_async_wrapper,
        agentops_tracer,
    )

    # Also patch _finalize_model_response_event to capture response attributes
    _patch(
        "google.adk.flows.llm_flows.base_llm_flow",
        "BaseLlmFlow",
        "_finalize_model_response_event",
        _finalize_model_response_event_wrapper,
        agentops_tracer,
    )

    # Patch tool execution to create merged tool spans
    _patch_module_function(
        "google.adk.flows.llm_flows.functions", "__call_tool_async", _call_tool_async_wrapper, agentops_tracer
    )

    logger.info("Google ADK patching complete")


def unpatch_adk():
    """Remove all patches from Google ADK modules."""
    logger.debug("Removing Google ADK patches")

    # Restore ADK's tracer
    try:
        import google.adk.telemetry as adk_telemetry
        from opentelemetry import trace

        adk_telemetry.tracer = trace.get_tracer("gcp.vertex.agent")
        logger.debug("Restored ADK's built-in tracer")
    except Exception as e:
        logger.warning(f"Failed to restore ADK tracer: {e}")

    # Unwrap all methods
    for obj, method_name in _wrapped_methods:
        try:
            if hasattr(getattr(obj, method_name), "__wrapped__"):
                original = getattr(obj, method_name).__wrapped__
                setattr(obj, method_name, original)
                logger.debug(f"Successfully unwrapped {obj}.{method_name}")
        except Exception as e:
            logger.warning(f"Failed to unwrap {obj}.{method_name}: {e}")

    _wrapped_methods.clear()
    logger.info("Google ADK unpatching complete")
