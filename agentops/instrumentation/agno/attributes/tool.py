"""Agno tool execution attributes handler."""

import json
from typing import Optional, Tuple, Dict, Any

from agentops.logging import logger
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes
from agentops.semconv.span_kinds import SpanKind as AgentOpsSpanKind


def get_tool_decorator_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract span attributes for tool decorator calls.

    The @tool decorator has multiple calling patterns:
    1. @tool - direct decoration, args[0] is the function
    2. @tool() - parameterless call, return_value is a decorator function
    3. @tool(name="...") - parameterized call, return_value is a decorator function

    Args:
        args: Positional arguments passed to the tool decorator
        kwargs: Keyword arguments passed to the tool decorator  
        return_value: The return value from the tool decorator

    Returns:
        A dictionary of span attributes to be set on the tool span
    """
    attributes: AttributeMap = {}

    # Base attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.TOOL
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"
    attributes["agno.tool.operation"] = "create"

    # Determine the calling pattern
    direct_decoration = (
        args and len(args) == 1 and callable(args[0]) and not kwargs
    )
    
    if direct_decoration:
        # Pattern 1: @tool (direct decoration)
        func = args[0]
        attributes["agno.tool.call_pattern"] = "direct"
        attributes["agno.tool.function_name"] = func.__name__
        
        # Check if it's an async function
        from inspect import iscoroutinefunction, isasyncgenfunction
        if iscoroutinefunction(func):
            attributes["agno.tool.function_type"] = "async"
        elif isasyncgenfunction(func):
            attributes["agno.tool.function_type"] = "async_generator"
        else:
            attributes["agno.tool.function_type"] = "sync"
            
        # Get docstring if available
        if func.__doc__:
            docstring = func.__doc__.strip()
            if len(docstring) > 200:
                docstring = docstring[:197] + "..."
            attributes["agno.tool.function_docstring"] = docstring
            
        # Since it's direct decoration, return_value should be a Function
        if return_value and hasattr(return_value, 'name'):
            attributes["agno.tool.created_name"] = str(return_value.name)
            
    else:
        # Pattern 2 & 3: @tool() or @tool(name="...") - parameterized decoration
        attributes["agno.tool.call_pattern"] = "parameterized"
        
        # Process decorator arguments from kwargs
        if kwargs:
            if kwargs.get('name'):
                attributes["agno.tool.config_name"] = kwargs['name']
            
            if kwargs.get('description'):
                attributes["agno.tool.config_description"] = kwargs['description']
                
            if kwargs.get('instructions'):
                attributes["agno.tool.config_instructions"] = kwargs['instructions']
                
            if 'strict' in kwargs and kwargs['strict'] is not None:
                attributes["agno.tool.config_strict"] = str(kwargs['strict'])
                
            if 'show_result' in kwargs and kwargs['show_result'] is not None:
                attributes["agno.tool.config_show_result"] = str(kwargs['show_result'])
                
            if 'stop_after_tool_call' in kwargs and kwargs['stop_after_tool_call'] is not None:
                attributes["agno.tool.config_stop_after_tool_call"] = str(kwargs['stop_after_tool_call'])
                
            if 'requires_confirmation' in kwargs and kwargs['requires_confirmation'] is not None:
                attributes["agno.tool.config_requires_confirmation"] = str(kwargs['requires_confirmation'])
                
            if 'requires_user_input' in kwargs and kwargs['requires_user_input'] is not None:
                attributes["agno.tool.config_requires_user_input"] = str(kwargs['requires_user_input'])
                
            if 'external_execution' in kwargs and kwargs['external_execution'] is not None:
                attributes["agno.tool.config_external_execution"] = str(kwargs['external_execution'])
                
            if kwargs.get('user_input_fields'):
                attributes["agno.tool.config_user_input_fields_count"] = str(len(kwargs['user_input_fields']))
                
            if 'cache_results' in kwargs and kwargs['cache_results'] is not None:
                attributes["agno.tool.config_cache_results"] = str(kwargs['cache_results'])
                
            if kwargs.get('cache_dir'):
                attributes["agno.tool.config_cache_dir"] = kwargs['cache_dir']
                
            if 'cache_ttl' in kwargs and kwargs['cache_ttl'] is not None:
                attributes["agno.tool.config_cache_ttl"] = str(kwargs['cache_ttl'])

        # For parameterized calls, return_value is a decorator function
        if return_value and callable(return_value):
            attributes["agno.tool.returns_decorator"] = "true"

    return attributes


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

    # Base attributes - Use "tool.usage" to match yellow color coding in frontend
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = "tool.usage"
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"
    attributes["agno.tool.operation"] = "execute"

    # Standard AgentOps attributes for consistency with other tool spans
    attributes["deployment.environment"] = "default_environment"
    attributes["service.name"] = "default_application"
    attributes["telemetry.sdk.name"] = "agentops"

    # Add execution context and debugging information
    import time
    import traceback
    
    attributes["agno.tool.execution_timestamp"] = str(int(time.time() * 1000))
    
    # Try to get calling context for debugging
    try:
        stack = traceback.extract_stack()
        # Look for relevant calling frames
        calling_info = []
        for frame in stack[-10:]:  # Last 10 frames
            if any(keyword in frame.filename.lower() for keyword in ['agno', 'agent', 'team', 'tool']):
                calling_info.append(f"{frame.filename.split('/')[-1]}:{frame.lineno}:{frame.name}")
        
        if calling_info:
            attributes["agno.tool.call_stack"] = " -> ".join(calling_info[-3:])  # Last 3 relevant frames
    except Exception as e:
        attributes["agno.tool.call_stack_error"] = str(e)

    # Process the FunctionCall object (self in execute method)
    if args and len(args) > 0:
        function_call = args[0]
        
        # Add detailed function call information
        attributes["agno.tool.function_call_type"] = str(type(function_call).__name__)
        
        # Extract tool information
        if hasattr(function_call, 'function') and function_call.function:
            function = function_call.function
            tool_name = getattr(function, 'name', 'unknown_tool')
            
            # Set span attributes for the tool execution span
            attributes["tool.name"] = tool_name
            attributes["agno.tool.function_name"] = tool_name
            
            # Function details and context
            if hasattr(function, 'description'):
                description = getattr(function, 'description', '')
                if description:
                    # Truncate long descriptions but keep them readable
                    if len(description) > 300:
                        description = description[:297] + "..."
                    attributes["tool.description"] = description
                    attributes["agno.tool.function_description"] = description
            
            # Function source information
            if hasattr(function, 'entrypoint') and function.entrypoint:
                entrypoint = function.entrypoint
                if hasattr(entrypoint, '__module__'):
                    attributes["agno.tool.function_module"] = str(entrypoint.__module__)
                if hasattr(entrypoint, '__name__'):
                    attributes["agno.tool.function_method"] = str(entrypoint.__name__)
                if hasattr(entrypoint, '__qualname__'):
                    attributes["agno.tool.function_qualname"] = str(entrypoint.__qualname__)
            
            # Tool capabilities
            if hasattr(function, 'requires_confirmation'):
                attributes["agno.tool.requires_confirmation"] = str(function.requires_confirmation)
            if hasattr(function, 'show_result'):
                attributes["agno.tool.show_result"] = str(function.show_result)
            if hasattr(function, 'stop_after_tool_call'):
                attributes["agno.tool.stop_after_tool_call"] = str(function.stop_after_tool_call)
            
            # Extract tool arguments with better formatting
            if hasattr(function_call, 'arguments') and function_call.arguments:
                try:
                    if isinstance(function_call.arguments, str):
                        args_dict = json.loads(function_call.arguments)
                    else:
                        args_dict = function_call.arguments
                    
                    # Format arguments nicely
                    formatted_args = []
                    for key, value in args_dict.items():
                        value_str = str(value)
                        if len(value_str) > 100:
                            value_str = value_str[:97] + "..."
                        formatted_args.append(f"{key}={value_str}")
                    
                    attributes["tool.parameters"] = json.dumps(args_dict)
                    attributes["agno.tool.formatted_args"] = ", ".join(formatted_args)
                    attributes["agno.tool.args_count"] = str(len(args_dict))
                except Exception as e:
                    attributes["tool.parameters"] = str(function_call.arguments)
                    attributes["agno.tool.args_parse_error"] = str(e)
        
        # Extract call ID and metadata
        if hasattr(function_call, 'tool_call_id'):
            attributes["agno.tool.call_id"] = str(function_call.tool_call_id)
        
        # Check for any agent context
        if hasattr(function_call, '_agent') and function_call._agent:
            agent = function_call._agent
            if hasattr(agent, 'name'):
                attributes["agno.tool.calling_agent_name"] = str(agent.name)
            if hasattr(agent, 'agent_id'):
                attributes["agno.tool.calling_agent_id"] = str(agent.agent_id)

    # Process return value
    if return_value is not None:
        # Add timing information
        import time
        attributes["agno.tool.execution_timestamp"] = str(int(time.time() * 1000))
        
        # Determine execution status and result information
        if hasattr(return_value, 'value'):
            # FunctionExecutionResult with value
            result_value = return_value.value
            attributes["agno.tool.execution_status"] = "success"
        else:
            # Direct return value
            result_value = return_value
            attributes["agno.tool.execution_status"] = "success"
        
        # Process result value
        if result_value is not None:
            result_type = type(result_value).__name__
            attributes["agno.tool.result_type"] = result_type
            
            # Handle FunctionExecutionResult objects specifically
            if hasattr(result_value, 'status') and hasattr(result_value, 'result'):
                # This looks like a FunctionExecutionResult
                status = getattr(result_value, 'status', 'unknown')
                actual_result = getattr(result_value, 'result', None)
                error = getattr(result_value, 'error', None)
                
                attributes["agno.tool.execution_result_status"] = str(status)
                attributes["tool.status"] = str(status)
                
                if error:
                    attributes["agno.tool.execution_error"] = str(error)
                    attributes["tool.error"] = str(error)
                
                if actual_result is not None:
                    actual_result_type = type(actual_result).__name__
                    attributes["agno.tool.actual_result_type"] = actual_result_type
                    
                    # Enhanced generator handling
                    if hasattr(actual_result, '__iter__') and hasattr(actual_result, '__next__'):
                        attributes["agno.tool.result_is_generator"] = "true"
                        
                        # Try to get more meaningful information about the generator
                        generator_info = []
                        
                        # Get function name from the generator
                        if hasattr(actual_result, 'gi_code'):
                            func_name = actual_result.gi_code.co_name
                            attributes["agno.tool.generator_function"] = func_name
                            generator_info.append(f"function={func_name}")
                        
                        # Get local variables from generator frame for context
                        if hasattr(actual_result, 'gi_frame') and actual_result.gi_frame:
                            try:
                                locals_dict = actual_result.gi_frame.f_locals
                                # Look for interesting variables that give context
                                context_vars = ['task_description', 'expected_output', 'member_agent', 'agent_name', 'team', 'message']
                                for var_name in context_vars:
                                    if var_name in locals_dict:
                                        value = str(locals_dict[var_name])
                                        if len(value) > 100:
                                            value = value[:97] + "..."
                                        generator_info.append(f"{var_name}={value}")
                                        attributes[f"agno.tool.generator_{var_name}"] = value
                                
                                # Count total local variables for debugging
                                attributes["agno.tool.generator_locals_count"] = str(len(locals_dict))
                            except Exception as e:
                                attributes["agno.tool.generator_locals_error"] = str(e)
                        
                        # Try to identify what type of transfer this is
                        generator_str = str(actual_result)
                        if 'transfer_task_to_member' in generator_str:
                            attributes["agno.tool.transfer_type"] = "task_to_member"
                        elif 'transfer' in generator_str.lower():
                            attributes["agno.tool.transfer_type"] = "general_transfer"
                        
                        if generator_info:
                            result_str = f"Generator<{actual_result_type}>({', '.join(generator_info)})"
                        else:
                            result_str = f"Generator<{actual_result_type}> - {str(actual_result)}"
                    else:
                        # Regular result - safe to convert to string
                        result_str = str(actual_result)
                        if len(result_str) > 500:
                            result_str = result_str[:497] + "..."
                else:
                    result_str = f"FunctionExecutionResult(status={status}, result=None)"
            else:
                # Not a FunctionExecutionResult, handle as direct result
                if hasattr(result_value, '__iter__') and hasattr(result_value, '__next__'):
                    # It's a generator
                    attributes["agno.tool.result_is_generator"] = "true"
                    
                    if hasattr(result_value, 'gi_code'):
                        func_name = result_value.gi_code.co_name
                        attributes["agno.tool.generator_function"] = func_name
                        result_str = f"Generator<{result_type}> function={func_name} - {str(result_value)}"
                    else:
                        result_str = f"Generator<{result_type}> - {str(result_value)}"
                else:
                    # Regular result
                    result_str = str(result_value)
                    if len(result_str) > 500:
                        result_str = result_str[:497] + "..."
        else:
            result_str = "None"
            
        # Set the main result attribute
        attributes["tool.result"] = result_str
        
        # Add additional analysis attributes
        attributes["agno.tool.result_length"] = str(len(result_str))
        
        # Provide a preview for long results
        if len(result_str) > 100:
            preview = result_str[:97] + "..."
            attributes["agno.tool.result_preview"] = preview
        else:
            attributes["agno.tool.result_preview"] = result_str
    
    # Set final execution status
    if not attributes.get("tool.status"):
        attributes["tool.status"] = "success"
        
    # Add execution summary for debugging
    tool_name = attributes.get("tool.name", "unknown")
    call_type = attributes.get("agno.tool.transfer_type", "unknown")
    attributes["agno.tool.execution_summary"] = f"Tool '{tool_name}' executed with type '{call_type}'"

    return attributes


def get_function_constructor_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract span attributes for Function constructor calls.

    This captures when Function objects are created (which happens for all @tool decorators).

    Args:
        args: Positional arguments passed to Function.__init__ (self, ...)
        kwargs: Keyword arguments passed to Function.__init__
        return_value: The return value from Function.__init__ (None)

    Returns:
        A dictionary of span attributes to be set on the function creation span
    """
    attributes: AttributeMap = {}

    # Base attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.TOOL
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"
    attributes["agno.tool.operation"] = "function_create"
    
    # Try to find active agent span to establish proper hierarchy
    try:
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            # Check if there's an agent-related span in the context
            span_context = current_span.get_span_context()
            if span_context and span_context.is_valid:
                attributes["agno.tool.created_during_agent_run"] = "true"
            else:
                attributes["agno.tool.created_during_agent_run"] = "false"
        else:
            attributes["agno.tool.created_during_agent_run"] = "false"
    except Exception:
        attributes["agno.tool.created_during_agent_run"] = "unknown"

    # Extract Function constructor arguments
    if kwargs:
        if kwargs.get('name'):
            attributes["agno.function.name"] = kwargs['name']
        
        if kwargs.get('description'):
            description = kwargs['description']
            if len(description) > 200:
                description = description[:197] + "..."
            attributes["agno.function.description"] = description
            
        if kwargs.get('instructions'):
            instructions = kwargs['instructions']
            if len(instructions) > 200:
                instructions = instructions[:197] + "..."
            attributes["agno.function.instructions"] = instructions
            
        if 'strict' in kwargs and kwargs['strict'] is not None:
            attributes["agno.function.strict"] = str(kwargs['strict'])
            
        if 'show_result' in kwargs and kwargs['show_result'] is not None:
            attributes["agno.function.show_result"] = str(kwargs['show_result'])
            
        if 'stop_after_tool_call' in kwargs and kwargs['stop_after_tool_call'] is not None:
            attributes["agno.function.stop_after_tool_call"] = str(kwargs['stop_after_tool_call'])
            
        if 'requires_confirmation' in kwargs and kwargs['requires_confirmation'] is not None:
            attributes["agno.function.requires_confirmation"] = str(kwargs['requires_confirmation'])
            
        if 'requires_user_input' in kwargs and kwargs['requires_user_input'] is not None:
            attributes["agno.function.requires_user_input"] = str(kwargs['requires_user_input'])
            
        if 'external_execution' in kwargs and kwargs['external_execution'] is not None:
            attributes["agno.function.external_execution"] = str(kwargs['external_execution'])
            
        if kwargs.get('user_input_fields'):
            attributes["agno.function.user_input_fields_count"] = str(len(kwargs['user_input_fields']))
            
        if 'cache_results' in kwargs and kwargs['cache_results'] is not None:
            attributes["agno.function.cache_results"] = str(kwargs['cache_results'])
            
        if kwargs.get('cache_dir'):
            attributes["agno.function.cache_dir"] = kwargs['cache_dir']
            
        if 'cache_ttl' in kwargs and kwargs['cache_ttl'] is not None:
            attributes["agno.function.cache_ttl"] = str(kwargs['cache_ttl'])

        # Check the entrypoint function if available
        if kwargs.get('entrypoint') and callable(kwargs['entrypoint']):
            func = kwargs['entrypoint']
            
            # Check if it's an async function
            from inspect import iscoroutinefunction, isasyncgenfunction
            if iscoroutinefunction(func):
                attributes["agno.function.entrypoint_type"] = "async"
            elif isasyncgenfunction(func):
                attributes["agno.function.entrypoint_type"] = "async_generator"
            else:
                attributes["agno.function.entrypoint_type"] = "sync"
                
            # Get function name from entrypoint
            if hasattr(func, '__name__'):
                attributes["agno.function.entrypoint_name"] = func.__name__

    return attributes


def get_tool_preparation_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract span attributes for agent tool preparation.

    This captures when an agent processes and registers tools during determine_tools_for_model.

    Args:
        args: Positional arguments passed to determine_tools_for_model (self, model, session_id, ...)
        kwargs: Keyword arguments passed to determine_tools_for_model
        return_value: The return value from determine_tools_for_model (None)

    Returns:
        A dictionary of span attributes to be set on the tool preparation span
    """
    attributes: AttributeMap = {}

    # Base attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.WORKFLOW
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"
    attributes["agno.agent.operation"] = "prepare_tools"

    # Extract agent information from args[0] (self)
    if args and len(args) >= 1:
        agent = args[0]
        
        if hasattr(agent, 'name') and agent.name:
            attributes["agno.agent.name"] = agent.name
            
        if hasattr(agent, 'tools') and agent.tools:
            tools_count = len(agent.tools)
            attributes["agno.agent.tools_count"] = str(tools_count)
            
            # Capture tool names if available
            tool_names = []
            for tool in agent.tools:
                if hasattr(tool, 'name'):
                    tool_names.append(tool.name)
                elif hasattr(tool, '__name__'):
                    tool_names.append(tool.__name__)
                elif callable(tool):
                    tool_names.append(getattr(tool, '__name__', 'unknown'))
                    
            if tool_names:
                # Limit to first 5 tools to avoid overly long attributes
                limited_names = tool_names[:5]
                if len(tool_names) > 5:
                    limited_names.append(f"...+{len(tool_names)-5} more")
                attributes["agno.agent.tool_names"] = ",".join(limited_names)

        # Extract model information
        if len(args) >= 2:
            model = args[1]
            if hasattr(model, 'id'):
                attributes["agno.agent.model_id"] = str(model.id)
            if hasattr(model, 'provider'):
                attributes["agno.agent.model_provider"] = str(model.provider)

        # Extract session information
        if len(args) >= 3:
            session_id = args[2]
            if session_id:
                attributes["agno.agent.session_id"] = str(session_id)

    # Extract additional info from kwargs
    if kwargs:
        if kwargs.get('async_mode') is not None:
            attributes["agno.agent.async_mode"] = str(kwargs['async_mode'])
            
        if kwargs.get('knowledge_filters'):
            attributes["agno.agent.has_knowledge_filters"] = "true"
        else:
            attributes["agno.agent.has_knowledge_filters"] = "false"

    return attributes


def get_tool_registration_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract span attributes for individual tool registration via Function.from_callable.

    This captures when individual tools (callables) are converted to Function objects during agent tool preparation.

    Args:
        args: Positional arguments passed to Function.from_callable (callable, ...)
        kwargs: Keyword arguments passed to Function.from_callable
        return_value: The return value from Function.from_callable (Function object)

    Returns:
        A dictionary of span attributes to be set on the tool registration span
    """
    attributes: AttributeMap = {}

    # Base attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.TOOL
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"
    attributes["agno.tool.operation"] = "register"

    # Extract callable information from args[0]
    if args and len(args) >= 1:
        callable_func = args[0]
        
        if hasattr(callable_func, '__name__'):
            attributes["agno.tool.function_name"] = callable_func.__name__
            
        # Check if it's an async function
        from inspect import iscoroutinefunction, isasyncgenfunction
        if iscoroutinefunction(callable_func):
            attributes["agno.tool.function_type"] = "async"
        elif isasyncgenfunction(callable_func):
            attributes["agno.tool.function_type"] = "async_generator"
        else:
            attributes["agno.tool.function_type"] = "sync"
            
        # Get docstring if available
        if hasattr(callable_func, '__doc__') and callable_func.__doc__:
            docstring = callable_func.__doc__.strip()
            if len(docstring) > 200:
                docstring = docstring[:197] + "..."
            attributes["agno.tool.function_docstring"] = docstring

        # Check if it's already a Function object (has agno-specific attributes)
        if hasattr(callable_func, 'name'):
            attributes["agno.tool.source_name"] = str(callable_func.name)
        if hasattr(callable_func, 'description'):
            description = str(callable_func.description)
            if len(description) > 200:
                description = description[:197] + "..."
            attributes["agno.tool.source_description"] = description

    # Extract kwargs passed to from_callable
    if kwargs:
        if kwargs.get('strict') is not None:
            attributes["agno.tool.strict"] = str(kwargs['strict'])

    # Extract information from the created Function object
    if return_value and hasattr(return_value, 'name'):
        attributes["agno.tool.created_name"] = str(return_value.name)
        
        if hasattr(return_value, 'description'):
            description = str(return_value.description)
            if len(description) > 200:
                description = description[:197] + "..."
            attributes["agno.tool.created_description"] = description
            
        # Tool capabilities from the created Function
        if hasattr(return_value, 'requires_confirmation'):
            attributes["agno.tool.requires_confirmation"] = str(return_value.requires_confirmation)
            
        if hasattr(return_value, 'requires_user_input'):
            attributes["agno.tool.requires_user_input"] = str(return_value.requires_user_input)
            
        if hasattr(return_value, 'external_execution'):
            attributes["agno.tool.external_execution"] = str(return_value.external_execution)

    return attributes 