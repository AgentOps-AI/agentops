"""Agno tool execution attributes handler."""

import json
from typing import Optional, Tuple, Dict, Any
import time
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes
from agentops.semconv.span_kinds import SpanKind as AgentOpsSpanKind
from agentops.semconv.tool import ToolAttributes


def get_tool_execution_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract span attributes for tool execution calls (FunctionCall.execute/aexecute).

    Args:
        args: Positional arguments passed to the execute method (self)
        kwargs: Keyword arguments passed to the execute method
        return_value: The return value from the execute method (FunctionExecutionResult)

    Returns:
        A dictionary of span attributes to be set on the tool execution span
    """
    attributes: AttributeMap = {}

    # Base attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.TOOL
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"

    # AgentOps entity attributes
    attributes[SpanAttributes.AGENTOPS_ENTITY_NAME] = "tool"

    # Process the FunctionCall object (self in execute method)
    if args and len(args) > 0:
        function_call = args[0]

        # Add detailed function call information
        attributes["tool.function_call_type"] = str(type(function_call).__name__)

        # Extract tool information
        if hasattr(function_call, "function") and function_call.function:
            function = function_call.function

            # Get function name and add display name
            if hasattr(function, "__name__"):
                func_name = function.__name__
                attributes["tool.function_name"] = func_name
                attributes["tool.display_name"] = f"{func_name} (Tool)"

            tool_name = getattr(function, "name", "unknown_tool")

            # Set span attributes for the tool execution span
            attributes[ToolAttributes.TOOL_NAME] = tool_name
            attributes["tool.function_name"] = tool_name

            # Function details and context
            if hasattr(function, "description"):
                description = getattr(function, "description", "")
                if description:
                    attributes[ToolAttributes.TOOL_DESCRIPTION] = description
                    attributes["tool.function_description"] = description

            # Function source information
            if hasattr(function, "entrypoint") and function.entrypoint:
                entrypoint = function.entrypoint
                if hasattr(entrypoint, "__module__"):
                    attributes["tool.function_module"] = str(entrypoint.__module__)
                if hasattr(entrypoint, "__name__"):
                    attributes["tool.function_method"] = str(entrypoint.__name__)
                if hasattr(entrypoint, "__qualname__"):
                    attributes["tool.function_qualname"] = str(entrypoint.__qualname__)

            # Tool capabilities
            if hasattr(function, "requires_confirmation"):
                attributes["tool.requires_confirmation"] = str(function.requires_confirmation)
            if hasattr(function, "show_result"):
                attributes["tool.show_result"] = str(function.show_result)
            if hasattr(function, "stop_after_tool_call"):
                attributes["tool.stop_after_tool_call"] = str(function.stop_after_tool_call)

            # Extract tool arguments with better formatting
            if hasattr(function_call, "arguments") and function_call.arguments:
                try:
                    if isinstance(function_call.arguments, str):
                        args_dict = json.loads(function_call.arguments)
                    else:
                        args_dict = function_call.arguments

                    # Format arguments nicely
                    formatted_args = []
                    for key, value in args_dict.items():
                        value_str = str(value)
                        formatted_args.append(f"{key}={value_str}")

                    attributes[ToolAttributes.TOOL_PARAMETERS] = json.dumps(args_dict)
                    attributes["tool.formatted_args"] = ", ".join(formatted_args)
                    attributes["tool.args_count"] = str(len(args_dict))
                except Exception as e:
                    attributes[ToolAttributes.TOOL_PARAMETERS] = str(function_call.arguments)
                    attributes["tool.args_parse_error"] = str(e)

        # Extract call ID and metadata
        if hasattr(function_call, "tool_call_id"):
            attributes["tool.call_id"] = str(function_call.tool_call_id)

        # Check for any agent context
        if hasattr(function_call, "_agent") and function_call._agent:
            agent = function_call._agent
            if hasattr(agent, "name"):
                attributes["tool.calling_agent_name"] = str(agent.name)
            if hasattr(agent, "agent_id"):
                attributes["tool.calling_agent_id"] = str(agent.agent_id)

    # Process return value
    if return_value is not None:
        # Add timing information
        attributes["tool.execution_timestamp"] = str(int(time.time() * 1000))

        # Determine execution status and result information
        if hasattr(return_value, "value"):
            # FunctionExecutionResult with value
            result_value = return_value.value
            attributes["tool.execution_status"] = "success"
        else:
            # Direct return value
            result_value = return_value
            attributes["tool.execution_status"] = "success"

        # Process result value
        if result_value is not None:
            result_type = type(result_value).__name__
            attributes["tool.execution_result_status"] = str(result_type)

            # Handle FunctionExecutionResult objects specifically
            if hasattr(result_value, "status") and hasattr(result_value, "result"):
                # This looks like a FunctionExecutionResult
                status = getattr(result_value, "status", "unknown")
                actual_result = getattr(result_value, "result", None)
                error = getattr(result_value, "error", None)

                attributes["tool.execution_result_status"] = str(status)
                attributes[ToolAttributes.TOOL_STATUS] = str(status)

                if error:
                    attributes["tool.execution_error"] = str(error)
                    attributes["tool.error"] = str(error)

                if actual_result is not None:
                    actual_result_type = type(actual_result).__name__
                    attributes["tool.actual_result_type"] = actual_result_type

                    # Enhanced generator handling
                    if hasattr(actual_result, "__iter__") and hasattr(actual_result, "__next__"):
                        attributes["tool.result_is_generator"] = "true"

                        # Try to get more meaningful information about the generator
                        generator_info = []

                        # Get function name from the generator
                        if hasattr(actual_result, "gi_code"):
                            func_name = actual_result.gi_code.co_name
                            attributes["tool.generator_function"] = func_name
                            generator_info.append(f"function={func_name}")

                        if generator_info:
                            result_str = f"Generator<{actual_result_type}>({', '.join(generator_info)})"
                        else:
                            result_str = f"Generator<{actual_result_type}> - {str(actual_result)}"
                    else:
                        # Regular result
                        result_str = str(actual_result)
                else:
                    result_str = str(status)
            else:
                # Not a FunctionExecutionResult, handle as direct result
                if hasattr(result_value, "__iter__") and hasattr(result_value, "__next__"):
                    # It's a generator
                    attributes["tool.result_is_generator"] = "true"

                    if hasattr(result_value, "gi_code"):
                        func_name = result_value.gi_code.co_name
                        attributes["tool.generator_function"] = func_name
                        result_str = f"Generator<{result_type}> function={func_name} - {str(result_value)}"
                    else:
                        result_str = f"Generator<{result_type}> - {str(result_value)}"
                else:
                    # Regular result
                    result_str = str(result_value)
        else:
            result_str = "None"

        # Set the main result attribute
        attributes[ToolAttributes.TOOL_RESULT] = result_str

        # Add additional analysis attributes
        attributes["tool.result_length"] = str(len(result_str))

    # Set final execution status
    if not attributes.get(ToolAttributes.TOOL_STATUS):
        attributes[ToolAttributes.TOOL_STATUS] = "success"

    # Add execution summary for debugging
    tool_name = attributes.get(ToolAttributes.TOOL_NAME, "unknown")
    call_type = attributes.get("tool.transfer_type", "unknown")
    attributes["tool.execution_summary"] = f"Tool '{tool_name}' executed with type '{call_type}'"

    return attributes
