
import asyncio
import functools
import json
import logging
import time
from typing import Any, Collection, Optional, Union, Set

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer, SpanKind, Status, StatusCode, get_current_span
from opentelemetry.metrics import get_meter

from agentops.semconv import (
    CoreAttributes,
    WorkflowAttributes,
    InstrumentationAttributes,
    AgentAttributes,
    SpanAttributes,
    Meters,
)
from agentops.logging import logger
from agentops.helpers.serialization import safe_serialize, model_to_dict
from agentops.instrumentation.openai_agents import get_model_info, __version__

class AgentsInstrumentor(BaseInstrumentor):
    """An instrumentor for OpenAI Agents SDK."""
    
    # Store original methods to restore later
    _original_methods = {}
    # Track active streaming operations
    _active_streaming_operations = set()
    # Metrics objects
    _agent_run_counter = None
    _agent_execution_time_histogram = None
    _agent_token_usage_histogram = None

    def instrumentation_dependencies(self) -> Collection[str]:
        return ["openai-agents >= 0.0.1"]

    def _instrument(self, **kwargs):
        """Instrument the Agents SDK."""
        tracer_provider = kwargs.get("tracer_provider")
        
        # Initialize metrics if a meter provider is available
        meter_provider = kwargs.get("meter_provider")
        if meter_provider:
            meter = get_meter(__name__, __version__, meter_provider)
            
            # Create metrics
            self.__class__._agent_run_counter = meter.create_counter(
                name="agents.runs", 
                unit="run", 
                description="Counts agent runs"
            )
            
            self.__class__._agent_execution_time_histogram = meter.create_histogram(
                name=Meters.LLM_OPERATION_DURATION, 
                unit="s", 
                description="GenAI operation duration"
            )
            
            self.__class__._agent_token_usage_histogram = meter.create_histogram(
                name=Meters.LLM_TOKEN_USAGE, 
                unit="token", 
                description="Measures token usage in agent runs"
            )

        # Add the custom processor to the Agents SDK
        try:
            from agents import add_trace_processor
            
            processor = AgentsDetailedProcessor()
            processor.exporter = AgentsDetailedExporter(tracer_provider)
            add_trace_processor(processor)
        except Exception as e:
            logger.warning(f"Failed to add AgentsDetailedProcessor: {e}")
        
        # Monkey patch the Runner class
        try:
            self._patch_runner_class(tracer_provider)
        except Exception as e:
            logger.warning(f"Failed to monkey patch Runner class: {e}")

    def _patch_runner_class(self, tracer_provider):
        """Monkey patch the Runner class to capture additional information."""
        from agents.run import Runner
        
        # Store original methods
        methods_to_patch = ["run_sync"]
        
        # Add async methods if they exist
        if hasattr(Runner, "run"):
            methods_to_patch.append("run")
        
        if hasattr(Runner, "run_streamed"):
            methods_to_patch.append("run_streamed")
        
        # Store original methods for later restoration
        for method_name in methods_to_patch:
            if hasattr(Runner, method_name):
                self.__class__._original_methods[method_name] = getattr(Runner, method_name)
        
        # Create instrumented version of run_sync (synchronous)
        def instrumented_run_sync(
            cls,
            starting_agent,
            input,
            context=None,
            max_turns=10,
            hooks=None,
            run_config=None,
        ):
            start_time = time.time()
            
            # Get the current tracer
            tracer = get_tracer(__name__, __version__, tracer_provider)
            
            # Extract model information
            model_info = get_model_info(starting_agent, run_config)
            model_name = model_info.get("model_name", "unknown")
            
            # Record agent run counter
            if self.__class__._agent_run_counter:
                self.__class__._agent_run_counter.add(
                    1,
                    {
                        "agent_name": starting_agent.name,
                        "method": "run_sync",
                        "stream": "false",
                        "model": model_name,
                    },
                )
            
            # Create span attributes
            attributes = {
                "span.kind": WorkflowAttributes.WORKFLOW_STEP,
                AgentAttributes.AGENT_NAME: starting_agent.name,
                WorkflowAttributes.WORKFLOW_INPUT: safe_serialize(input),
                WorkflowAttributes.MAX_TURNS: max_turns,
                "service.name": "agentops.agents",
                WorkflowAttributes.WORKFLOW_TYPE: "agents.run_sync",
                SpanAttributes.LLM_REQUEST_MODEL: model_name,
                SpanAttributes.LLM_SYSTEM: "openai",
                "stream": "false",
            }
            
            # Add model parameters from model_info
            for param, value in model_info.items():
                if param != "model_name":
                    attributes[f"agent.model.{param}"] = value
            
            # Create a default RunConfig if None is provided
            if run_config is None:
                from agents.run import RunConfig
                run_config = RunConfig(workflow_name=f"Agent {starting_agent.name}")
            
            # Add workflow name
            if hasattr(run_config, "workflow_name"):
                attributes[WorkflowAttributes.WORKFLOW_NAME] = run_config.workflow_name
            
            # Start a span for the run
            with tracer.start_as_current_span(
                name=f"agents.run_sync.{starting_agent.name}", 
                kind=SpanKind.CLIENT, 
                attributes=attributes
            ) as span:
                # Add agent attributes
                if hasattr(starting_agent, "instructions"):
                    # Determine instruction type
                    instruction_type = "unknown"
                    if isinstance(starting_agent.instructions, str):
                        instruction_type = "string"
                        span.set_attribute("agent.instructions", starting_agent.instructions)
                    elif callable(starting_agent.instructions):
                        instruction_type = "function"
                        func_name = getattr(starting_agent.instructions, "__name__", str(starting_agent.instructions))
                        span.set_attribute("agent.instruction_function", func_name)
                    else:
                        # Use safe_serialize for complex objects
                        instructions_dict = model_to_dict(starting_agent.instructions)
                        span.set_attribute("agent.instructions", safe_serialize(instructions_dict))
                    
                    span.set_attribute("agent.instruction_type", instruction_type)
                
                # Add agent tools if available
                if hasattr(starting_agent, "tools") and starting_agent.tools:
                    tool_names = [tool.name for tool in starting_agent.tools if hasattr(tool, "name")]
                    if tool_names:
                        span.set_attribute(AgentAttributes.AGENT_TOOLS, ",".join(tool_names))
                
                # Add agent model settings if available
                if hasattr(starting_agent, "model_settings") and starting_agent.model_settings:
                    # Add model settings directly using semantic conventions
                    for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
                        if hasattr(starting_agent.model_settings, param) and getattr(starting_agent.model_settings, param) is not None:
                            attr_name = getattr(SpanAttributes, f"LLM_REQUEST_{param.upper()}", f"gen_ai.request.{param}")
                            span.set_attribute(attr_name, getattr(starting_agent.model_settings, param))
                
                try:
                    # Execute the original method
                    original_method = self.__class__._original_methods["run_sync"]
                    result = original_method(
                        starting_agent,
                        input,
                        context=context,
                        max_turns=max_turns,
                        hooks=hooks,
                        run_config=run_config,
                    )
                    
                    # Add result attributes to the span
                    if hasattr(result, "final_output"):
                        span.set_attribute(WorkflowAttributes.FINAL_OUTPUT, safe_serialize(result.final_output))
                    
                    # Process raw responses
                    if hasattr(result, "raw_responses") and result.raw_responses:
                        total_input_tokens = 0
                        total_output_tokens = 0
                        total_tokens = 0
                        
                        for i, response in enumerate(result.raw_responses):
                            # Try to extract model directly
                            if hasattr(response, "model"):
                                model_name = response.model
                                span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, model_name)
                            
                            # Extract usage information
                            if hasattr(response, "usage"):
                                usage = response.usage
                                
                                # Support both prompt_tokens and input_tokens
                                input_tokens = getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", 0))
                                if input_tokens:
                                    span.set_attribute(f"{SpanAttributes.LLM_USAGE_PROMPT_TOKENS}.{i}", input_tokens)
                                    total_input_tokens += input_tokens
                                    
                                    if self.__class__._agent_token_usage_histogram:
                                        self.__class__._agent_token_usage_histogram.record(
                                            input_tokens,
                                            {
                                                "token_type": "input",
                                                "model": model_name,
                                                SpanAttributes.LLM_REQUEST_MODEL: model_name,
                                                SpanAttributes.LLM_SYSTEM: "openai",
                                            },
                                        )
                                
                                # Support both completion_tokens and output_tokens
                                output_tokens = getattr(usage, "completion_tokens", getattr(usage, "output_tokens", 0))
                                if output_tokens:
                                    span.set_attribute(f"{SpanAttributes.LLM_USAGE_COMPLETION_TOKENS}.{i}", output_tokens)
                                    total_output_tokens += output_tokens
                                    
                                    if self.__class__._agent_token_usage_histogram:
                                        self.__class__._agent_token_usage_histogram.record(
                                            output_tokens,
                                            {
                                                "token_type": "output",
                                                "model": model_name,
                                                SpanAttributes.LLM_REQUEST_MODEL: model_name,
                                                SpanAttributes.LLM_SYSTEM: "openai",
                                            },
                                        )
                                
                                # Total tokens
                                if hasattr(usage, "total_tokens"):
                                    span.set_attribute(f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.{i}", usage.total_tokens)
                                    total_tokens += usage.total_tokens
                        
                        # Set total token counts
                        if total_input_tokens > 0:
                            span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, total_input_tokens)
                        
                        if total_output_tokens > 0:
                            span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, total_output_tokens)
                        
                        if total_tokens > 0:
                            span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, total_tokens)
                    
                    # Record execution time
                    execution_time = time.time() - start_time  # In seconds
                    if self.__class__._agent_execution_time_histogram:
                        # Create shared attributes following OpenAI conventions
                        shared_attributes = {
                            SpanAttributes.LLM_SYSTEM: "openai",
                            "gen_ai.response.model": model_name,
                            SpanAttributes.LLM_REQUEST_MODEL: model_name,
                            "gen_ai.operation.name": "agent_run",
                            "agent_name": starting_agent.name,
                            "stream": "false",
                        }
                        
                        self.__class__._agent_execution_time_histogram.record(
                            execution_time, 
                            attributes=shared_attributes
                        )
                    
                    # Add instrumentation metadata
                    span.set_attribute(InstrumentationAttributes.NAME, "agentops.agents")
                    span.set_attribute(InstrumentationAttributes.VERSION, __version__)
                    
                    return result
                except Exception as e:
                    # Record the error
                    span.set_status(Status(StatusCode.ERROR))
                    span.record_exception(e)
                    span.set_attribute(CoreAttributes.ERROR_TYPE, type(e).__name__)
                    span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
                    raise
        
        # Create async instrumented version if needed
        if "run" in self.__class__._original_methods:
            async def instrumented_run(
                cls,
                starting_agent,
                input,
                context=None,
                max_turns=10,
                hooks=None,
                run_config=None,
            ):
                start_time = time.time()
                
                # Get the current tracer
                tracer = get_tracer(__name__, __version__, tracer_provider)
                
                # Extract model information
                model_info = get_model_info(starting_agent, run_config)
                model_name = model_info.get("model_name", "unknown")
                
                # Record agent run counter
                if self.__class__._agent_run_counter:
                    self.__class__._agent_run_counter.add(
                        1,
                        {
                            "agent_name": starting_agent.name,
                            "method": "run",
                            "stream": "false",
                            "model": model_name,
                        },
                    )
                
                # Create span attributes
                attributes = {
                    "span.kind": WorkflowAttributes.WORKFLOW_STEP,
                    AgentAttributes.AGENT_NAME: starting_agent.name,
                    WorkflowAttributes.WORKFLOW_INPUT: safe_serialize(input),
                    WorkflowAttributes.MAX_TURNS: max_turns,
                    "service.name": "agentops.agents",
                    WorkflowAttributes.WORKFLOW_TYPE: "agents.run",
                    SpanAttributes.LLM_REQUEST_MODEL: model_name,
                    SpanAttributes.LLM_SYSTEM: "openai",
                    "stream": "false",
                }
                
                # Add model parameters from model_info
                for param, value in model_info.items():
                    if param != "model_name":
                        attributes[f"agent.model.{param}"] = value
                
                # Create a default RunConfig if None is provided
                if run_config is None:
                    from agents.run import RunConfig
                    run_config = RunConfig(workflow_name=f"Agent {starting_agent.name}")
                
                # Add workflow name
                if hasattr(run_config, "workflow_name"):
                    attributes[WorkflowAttributes.WORKFLOW_NAME] = run_config.workflow_name
                
                # Start a span for the run
                with tracer.start_as_current_span(
                    name=f"agents.run.{starting_agent.name}", 
                    kind=SpanKind.CLIENT, 
                    attributes=attributes
                ) as span:
                    # Add agent attributes
                    if hasattr(starting_agent, "instructions"):
                        # Determine instruction type
                        instruction_type = "unknown"
                        if isinstance(starting_agent.instructions, str):
                            instruction_type = "string"
                            span.set_attribute("agent.instructions", starting_agent.instructions)
                        elif callable(starting_agent.instructions):
                            instruction_type = "function"
                            func_name = getattr(starting_agent.instructions, "__name__", str(starting_agent.instructions))
                            span.set_attribute("agent.instruction_function", func_name)
                        else:
                            span.set_attribute("agent.instructions", safe_serialize(starting_agent.instructions))
                        
                        span.set_attribute("agent.instruction_type", instruction_type)
                    
                    # Add agent tools if available
                    if hasattr(starting_agent, "tools") and starting_agent.tools:
                        tool_names = [tool.name for tool in starting_agent.tools if hasattr(tool, "name")]
                        if tool_names:
                            span.set_attribute(AgentAttributes.AGENT_TOOLS, ",".join(tool_names))
                    
                    # Add agent model settings if available
                    if hasattr(starting_agent, "model_settings") and starting_agent.model_settings:
                        # Add model settings directly using semantic conventions
                        for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
                            if hasattr(starting_agent.model_settings, param) and getattr(starting_agent.model_settings, param) is not None:
                                attr_name = getattr(SpanAttributes, f"LLM_REQUEST_{param.upper()}", f"gen_ai.request.{param}")
                                span.set_attribute(attr_name, getattr(starting_agent.model_settings, param))
                    
                    try:
                        # Execute the original method
                        original_method = self.__class__._original_methods["run"]
                        result = await original_method(
                            starting_agent,
                            input,
                            context=context,
                            max_turns=max_turns,
                            hooks=hooks,
                            run_config=run_config,
                        )
                        
                        # Add result attributes to the span
                        if hasattr(result, "final_output"):
                            span.set_attribute(WorkflowAttributes.FINAL_OUTPUT, safe_serialize(result.final_output))
                        
                        # Process raw responses
                        if hasattr(result, "raw_responses") and result.raw_responses:
                            total_input_tokens = 0
                            total_output_tokens = 0
                            total_tokens = 0
                            
                            for i, response in enumerate(result.raw_responses):
                                # Try to extract model directly
                                if hasattr(response, "model"):
                                    model_name = response.model
                                    span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, model_name)
                                
                                # Extract usage information
                                if hasattr(response, "usage"):
                                    usage = response.usage
                                    
                                    # Support both prompt_tokens and input_tokens
                                    input_tokens = getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", 0))
                                    if input_tokens:
                                        span.set_attribute(f"{SpanAttributes.LLM_USAGE_PROMPT_TOKENS}.{i}", input_tokens)
                                        total_input_tokens += input_tokens
                                        
                                        if self.__class__._agent_token_usage_histogram:
                                            self.__class__._agent_token_usage_histogram.record(
                                                input_tokens,
                                                {
                                                    "token_type": "input",
                                                    "model": model_name,
                                                    SpanAttributes.LLM_REQUEST_MODEL: model_name,
                                                    SpanAttributes.LLM_SYSTEM: "openai",
                                                },
                                            )
                                    
                                    # Support both completion_tokens and output_tokens
                                    output_tokens = getattr(usage, "completion_tokens", getattr(usage, "output_tokens", 0))
                                    if output_tokens:
                                        span.set_attribute(f"{SpanAttributes.LLM_USAGE_COMPLETION_TOKENS}.{i}", output_tokens)
                                        total_output_tokens += output_tokens
                                        
                                        if self.__class__._agent_token_usage_histogram:
                                            self.__class__._agent_token_usage_histogram.record(
                                                output_tokens,
                                                {
                                                    "token_type": "output",
                                                    "model": model_name,
                                                    SpanAttributes.LLM_REQUEST_MODEL: model_name,
                                                    SpanAttributes.LLM_SYSTEM: "openai",
                                                },
                                            )
                                    
                                    # Total tokens
                                    if hasattr(usage, "total_tokens"):
                                        span.set_attribute(f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.{i}", usage.total_tokens)
                                        total_tokens += usage.total_tokens
                            
                            # Set total token counts
                            if total_input_tokens > 0:
                                span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, total_input_tokens)
                            
                            if total_output_tokens > 0:
                                span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, total_output_tokens)
                            
                            if total_tokens > 0:
                                span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, total_tokens)
                        
                        # Record execution time
                        execution_time = time.time() - start_time  # In seconds
                        if self.__class__._agent_execution_time_histogram:
                            # Create shared attributes following OpenAI conventions
                            shared_attributes = {
                                SpanAttributes.LLM_SYSTEM: "openai",
                                "gen_ai.response.model": model_name,
                                SpanAttributes.LLM_REQUEST_MODEL: model_name,
                                "gen_ai.operation.name": "agent_run",
                                "agent_name": starting_agent.name,
                                "stream": "false",
                            }
                            
                            self.__class__._agent_execution_time_histogram.record(
                                execution_time, 
                                attributes=shared_attributes
                            )
                        
                        # Add instrumentation metadata
                        span.set_attribute(InstrumentationAttributes.NAME, "agentops.agents")
                        span.set_attribute(InstrumentationAttributes.VERSION, __version__)
                        
                        return result
                    except Exception as e:
                        # Record the error
                        span.set_status(Status(StatusCode.ERROR))
                        span.record_exception(e)
                        span.set_attribute(CoreAttributes.ERROR_TYPE, type(e).__name__)
                        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
                        raise
        
        # Streaming run implementation (simplified)
        if "run_streamed" in self.__class__._original_methods:
            def instrumented_run_streamed(
                cls,
                starting_agent,
                input,
                context=None,
                max_turns=10,
                hooks=None,
                run_config=None,
            ):
                start_time = time.time()
                
                # Get the current tracer
                tracer = get_tracer(__name__, __version__, tracer_provider)
                
                # Extract model information
                model_info = get_model_info(starting_agent, run_config)
                model_name = model_info.get("model_name", "unknown")
                
                # Record agent run counter
                if self.__class__._agent_run_counter:
                    self.__class__._agent_run_counter.add(
                        1,
                        {
                            "agent_name": starting_agent.name,
                            "method": "run_streamed",
                            "stream": "true",
                            "model": model_name,
                        },
                    )
                
                # Create span attributes
                attributes = {
                    "span.kind": WorkflowAttributes.WORKFLOW_STEP,
                    AgentAttributes.AGENT_NAME: starting_agent.name,
                    WorkflowAttributes.WORKFLOW_INPUT: safe_serialize(input),
                    WorkflowAttributes.MAX_TURNS: max_turns,
                    "service.name": "agentops.agents",
                    WorkflowAttributes.WORKFLOW_TYPE: "agents.run_streamed",
                    SpanAttributes.LLM_REQUEST_MODEL: model_name,
                    SpanAttributes.LLM_SYSTEM: "openai",
                    "stream": "true",
                }
                
                # Add model parameters from model_info
                for param, value in model_info.items():
                    if param != "model_name":
                        attributes[f"agent.model.{param}"] = value
                
                # Create a default RunConfig if None is provided
                if run_config is None:
                    from agents.run import RunConfig
                    run_config = RunConfig(workflow_name=f"Agent {starting_agent.name}")
                
                # Add workflow name
                if hasattr(run_config, "workflow_name"):
                    attributes[WorkflowAttributes.WORKFLOW_NAME] = run_config.workflow_name
                
                # Start a span for the run
                with tracer.start_as_current_span(
                    name=f"agents.run_streamed.{starting_agent.name}", 
                    kind=SpanKind.CLIENT, 
                    attributes=attributes
                ) as span:
                    # Add agent attributes
                    if hasattr(starting_agent, "instructions"):
                        # Determine instruction type
                        instruction_type = "unknown"
                        if isinstance(starting_agent.instructions, str):
                            instruction_type = "string"
                            span.set_attribute("agent.instructions", starting_agent.instructions)
                        elif callable(starting_agent.instructions):
                            instruction_type = "function"
                            func_name = getattr(starting_agent.instructions, "__name__", str(starting_agent.instructions))
                            span.set_attribute("agent.instruction_function", func_name)
                        else:
                            span.set_attribute("agent.instructions", safe_serialize(starting_agent.instructions))
                        
                        span.set_attribute("agent.instruction_type", instruction_type)
                    
                    # Add agent tools if available
                    if hasattr(starting_agent, "tools") and starting_agent.tools:
                        tool_names = [tool.name for tool in starting_agent.tools if hasattr(tool, "name")]
                        if tool_names:
                            span.set_attribute(AgentAttributes.AGENT_TOOLS, ",".join(tool_names))
                    
                    # Add agent model settings if available
                    if hasattr(starting_agent, "model_settings") and starting_agent.model_settings:
                        # Add model settings directly using semantic conventions
                        for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
                            if hasattr(starting_agent.model_settings, param) and getattr(starting_agent.model_settings, param) is not None:
                                attr_name = getattr(SpanAttributes, f"LLM_REQUEST_{param.upper()}", f"gen_ai.request.{param}")
                                span.set_attribute(attr_name, getattr(starting_agent.model_settings, param))
                    
                    try:
                        # Execute the original method
                        original_method = self.__class__._original_methods["run_streamed"]
                        result = original_method(
                            starting_agent,
                            input,
                            context=context,
                            max_turns=max_turns,
                            hooks=hooks,
                            run_config=run_config,
                        )
                        
                        # Create a unique identifier for this streaming operation
                        stream_id = id(result)
                        self.__class__._active_streaming_operations.add(stream_id)
                        
                        # Get the original stream_events method
                        original_stream_events = result.stream_events
                        
                        # Create an instrumented version of stream_events
                        @functools.wraps(original_stream_events)
                        async def instrumented_stream_events():
                            try:
                                # Use the original stream_events method
                                async for event in original_stream_events():
                                    yield event
                                
                                # After streaming completes, capture metrics and update spans
                                execution_time = time.time() - start_time  # In seconds
                                
                                # Create a new span for token usage metrics to avoid span closure issues
                                usage_tracer = get_tracer(__name__, __version__, tracer_provider)
                                
                                # Create attributes for the new span
                                usage_attributes = {
                                    "span.kind": SpanKind.INTERNAL,
                                    AgentAttributes.AGENT_NAME: starting_agent.name,
                                    "service.name": "agentops.agents",
                                    WorkflowAttributes.WORKFLOW_TYPE: "agents.run_streamed.usage",
                                    SpanAttributes.LLM_REQUEST_MODEL: model_name,
                                    SpanAttributes.LLM_SYSTEM: "openai",
                                    "stream": "true",
                                    "stream_id": str(stream_id),
                                }
                                
                                # Start a new span for token usage metrics
                                with usage_tracer.start_as_current_span(
                                    name=f"agents.run_streamed.usage.{starting_agent.name}",
                                    kind=SpanKind.INTERNAL,
                                    attributes=usage_attributes,
                                ) as usage_span:
                                    # Add result attributes to the span
                                    if hasattr(result, "final_output"):
                                        usage_span.set_attribute(
                                            WorkflowAttributes.FINAL_OUTPUT, str(result.final_output)[:1000]
                                        )
                                    
                                    # Process raw responses for token usage
                                    if hasattr(result, "raw_responses") and result.raw_responses:
                                        total_input_tokens = 0
                                        total_output_tokens = 0
                                        total_tokens = 0
                                        
                                        for i, response in enumerate(result.raw_responses):
                                            # Extract usage information
                                            if hasattr(response, "usage"):
                                                usage = response.usage
                                                
                                                # Support both prompt_tokens and input_tokens
                                                input_tokens = getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", 0))
                                                if input_tokens:
                                                    usage_span.set_attribute(f"{SpanAttributes.LLM_USAGE_PROMPT_TOKENS}.{i}", input_tokens)
                                                    total_input_tokens += input_tokens
                                                    
                                                    if self.__class__._agent_token_usage_histogram:
                                                        self.__class__._agent_token_usage_histogram.record(
                                                            input_tokens,
                                                            {
                                                                "token_type": "input",
                                                                "model": model_name,
                                                                SpanAttributes.LLM_REQUEST_MODEL: model_name,
                                                                SpanAttributes.LLM_SYSTEM: "openai",
                                                            },
                                                        )
                                                
                                                # Support both completion_tokens and output_tokens
                                                output_tokens = getattr(usage, "completion_tokens", getattr(usage, "output_tokens", 0))
                                                if output_tokens:
                                                    usage_span.set_attribute(f"{SpanAttributes.LLM_USAGE_COMPLETION_TOKENS}.{i}", output_tokens)
                                                    total_output_tokens += output_tokens
                                                    
                                                    if self.__class__._agent_token_usage_histogram:
                                                        self.__class__._agent_token_usage_histogram.record(
                                                            output_tokens,
                                                            {
                                                                "token_type": "output",
                                                                "model": model_name,
                                                                SpanAttributes.LLM_REQUEST_MODEL: model_name,
                                                                SpanAttributes.LLM_SYSTEM: "openai",
                                                            },
                                                        )
                                                
                                                # Total tokens
                                                if hasattr(usage, "total_tokens"):
                                                    usage_span.set_attribute(f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.{i}", usage.total_tokens)
                                                    total_tokens += usage.total_tokens
                                        
                                        # Set total token counts
                                        if total_input_tokens > 0:
                                            usage_span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, total_input_tokens)
                                        
                                        if total_output_tokens > 0:
                                            usage_span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, total_output_tokens)
                                        
                                        if total_tokens > 0:
                                            usage_span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, total_tokens)
                                    
                                    # Record execution time
                                    if self.__class__._agent_execution_time_histogram:
                                        # Create shared attributes following OpenAI conventions
                                        shared_attributes = {
                                            SpanAttributes.LLM_SYSTEM: "openai",
                                            "gen_ai.response.model": model_name,
                                            SpanAttributes.LLM_REQUEST_MODEL: model_name,
                                            "gen_ai.operation.name": "agent_run",
                                            "agent_name": starting_agent.name,
                                            "stream": "true",
                                        }
                                        
                                        self.__class__._agent_execution_time_histogram.record(
                                            execution_time, 
                                            attributes=shared_attributes
                                        )
                                    
                                    # Add instrumentation metadata
                                    usage_span.set_attribute(InstrumentationAttributes.NAME, "agentops.agents")
                                    usage_span.set_attribute(InstrumentationAttributes.VERSION, __version__)
                                
                            except Exception as e:
                                logger.warning(f"Error in instrumented_stream_events: {e}")
                            finally:
                                # Remove this streaming operation from the active set
                                if stream_id in self.__class__._active_streaming_operations:
                                    self.__class__._active_streaming_operations.remove(stream_id)
                        
                        # Replace the original stream_events method with our instrumented version
                        result.stream_events = instrumented_stream_events
                        
                        return result
                    except Exception as e:
                        # Record the error
                        span.set_status(Status(StatusCode.ERROR))
                        span.record_exception(e)
                        span.set_attribute(CoreAttributes.ERROR_TYPE, type(e).__name__)
                        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
                        raise
        
        # Patch the Runner class methods
        setattr(Runner, "run_sync", classmethod(instrumented_run_sync))
        
        if "run" in self.__class__._original_methods:
            setattr(Runner, "run", classmethod(instrumented_run))
        
        if "run_streamed" in self.__class__._original_methods:
            setattr(Runner, "run_streamed", classmethod(instrumented_run_streamed))

    def _uninstrument(self, **kwargs):
        """Uninstrument the Agents SDK."""
        # Restore original methods
        try:
            from agents.run import Runner
            
            # Restore original methods
            for method_name, original_method in self.__class__._original_methods.items():
                if hasattr(Runner, method_name):
                    setattr(Runner, method_name, original_method)
            
            # Clear stored methods
            self.__class__._original_methods.clear()
        except Exception as e:
            logger.warning(f"Failed to restore original Runner methods: {e}")
        
        # Clear active streaming operations
        self.__class__._active_streaming_operations.clear()
