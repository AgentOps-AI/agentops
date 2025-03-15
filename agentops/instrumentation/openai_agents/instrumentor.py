
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
            self._initialize_metrics(meter_provider)

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

    def _initialize_metrics(self, meter_provider):
        """Initialize metrics for the instrumentor."""
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
            self._record_agent_run(starting_agent.name, "run_sync", "false", model_name)
            
            # Create span attributes
            attributes = self._create_span_attributes(
                starting_agent, input, max_turns, model_name, "agents.run_sync", "false", model_info, run_config
            )
            
            # Start a span for the run
            with tracer.start_as_current_span(
                name=f"agents.run_sync.{starting_agent.name}", 
                kind=SpanKind.CLIENT, 
                attributes=attributes
            ) as span:
                # Add agent-specific attributes
                self._add_agent_attributes_to_span(span, starting_agent)
                
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
                    
                    # Process result and update span
                    self._process_result_and_update_span(
                        span, result, model_name, start_time, "false", starting_agent.name
                    )
                    
                    return result
                except Exception as e:
                    # Record the error
                    self._record_error_to_span(span, e)
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
                self._record_agent_run(starting_agent.name, "run", "false", model_name)
                
                # Create span attributes
                attributes = self._create_span_attributes(
                    starting_agent, input, max_turns, model_name, "agents.run", "false", model_info, run_config
                )
                
                # Start a span for the run
                with tracer.start_as_current_span(
                    name=f"agents.run.{starting_agent.name}", 
                    kind=SpanKind.CLIENT, 
                    attributes=attributes
                ) as span:
                    # Add agent-specific attributes
                    self._add_agent_attributes_to_span(span, starting_agent)
                    
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
                        
                        # Process result and update span
                        self._process_result_and_update_span(
                            span, result, model_name, start_time, "false", starting_agent.name
                        )
                        
                        return result
                    except Exception as e:
                        # Record the error
                        self._record_error_to_span(span, e)
                        raise
        
        # Streaming run implementation
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
                self._record_agent_run(starting_agent.name, "run_streamed", "true", model_name)
                
                # Create span attributes
                attributes = self._create_span_attributes(
                    starting_agent, input, max_turns, model_name, "agents.run_streamed", "true", model_info, run_config
                )
                
                # Start a span for the run
                with tracer.start_as_current_span(
                    name=f"agents.run_streamed.{starting_agent.name}", 
                    kind=SpanKind.CLIENT, 
                    attributes=attributes
                ) as span:
                    # Add agent-specific attributes
                    self._add_agent_attributes_to_span(span, starting_agent)
                    
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
                        
                        # Handle streaming operation
                        self._instrument_streaming_result(
                            result, model_name, starting_agent.name, start_time, tracer_provider
                        )
                        
                        return result
                    except Exception as e:
                        # Record the error
                        self._record_error_to_span(span, e)
                        raise
        
        # Patch the Runner class methods
        setattr(Runner, "run_sync", classmethod(instrumented_run_sync))
        
        if "run" in self.__class__._original_methods:
            setattr(Runner, "run", classmethod(instrumented_run))
        
        if "run_streamed" in self.__class__._original_methods:
            setattr(Runner, "run_streamed", classmethod(instrumented_run_streamed))

    def _instrument_streaming_result(self, result, model_name, agent_name, start_time, tracer_provider):
        """Set up instrumentation for streaming results."""
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
                self._process_streaming_completion(
                    result, model_name, agent_name, stream_id, start_time, tracer_provider
                )
                
            except Exception as e:
                logger.warning(f"Error in instrumented_stream_events: {e}")
            finally:
                # Remove this streaming operation from the active set
                if stream_id in self.__class__._active_streaming_operations:
                    self.__class__._active_streaming_operations.remove(stream_id)
        
        # Replace the original stream_events method with our instrumented version
        result.stream_events = instrumented_stream_events

    def _process_streaming_completion(self, result, model_name, agent_name, stream_id, start_time, tracer_provider):
        """Process the completion of a streaming operation."""
        execution_time = time.time() - start_time  # In seconds
        
        # Create a new span for token usage metrics to avoid span closure issues
        usage_tracer = get_tracer(__name__, __version__, tracer_provider)
        
        # Create attributes for the new span
        usage_attributes = {
            "span.kind": SpanKind.INTERNAL,
            AgentAttributes.AGENT_NAME: agent_name,
            "service.name": "agentops.agents",
            WorkflowAttributes.WORKFLOW_TYPE: "agents.run_streamed.usage",
            SpanAttributes.LLM_REQUEST_MODEL: model_name,
            SpanAttributes.LLM_SYSTEM: "openai",
            "stream": "true",
            "stream_id": str(stream_id),
        }
        
        # Start a new span for token usage metrics
        with usage_tracer.start_as_current_span(
            name=f"agents.run_streamed.usage.{agent_name}",
            kind=SpanKind.INTERNAL,
            attributes=usage_attributes,
        ) as usage_span:
            # Add result attributes to the span
            if hasattr(result, "final_output"):
                usage_span.set_attribute(
                    WorkflowAttributes.FINAL_OUTPUT, str(result.final_output)[:1000]
                )
            
            # Process token usage from responses
            self._process_token_usage_from_responses(usage_span, result, model_name)
            
            # Record execution time
            self._record_execution_time(execution_time, model_name, agent_name, "true")
            
            # Add instrumentation metadata
            self._add_instrumentation_metadata(usage_span)

    def _record_agent_run(self, agent_name, method, is_streaming, model_name):
        """Record an agent run in the counter metric."""
        if self.__class__._agent_run_counter:
            self.__class__._agent_run_counter.add(
                1,
                {
                    "agent_name": agent_name,
                    "method": method,
                    "stream": is_streaming,
                    "model": model_name,
                },
            )

    def _create_span_attributes(self, agent, input, max_turns, model_name, workflow_type, 
                              is_streaming, model_info, run_config):
        """Create the span attributes for an agent run."""
        attributes = {
            "span.kind": WorkflowAttributes.WORKFLOW_STEP,
            AgentAttributes.AGENT_NAME: agent.name,
            WorkflowAttributes.WORKFLOW_INPUT: safe_serialize(input),
            WorkflowAttributes.MAX_TURNS: max_turns,
            "service.name": "agentops.agents",
            WorkflowAttributes.WORKFLOW_TYPE: workflow_type,
            SpanAttributes.LLM_REQUEST_MODEL: model_name,
            SpanAttributes.LLM_SYSTEM: "openai",
            "stream": is_streaming,
        }
        
        # Add model parameters from model_info
        for param, value in model_info.items():
            if param != "model_name":
                attributes[f"agent.model.{param}"] = value
        
        # Create a default RunConfig if None is provided
        if run_config is None:
            from agents.run import RunConfig
            run_config = RunConfig(workflow_name=f"Agent {agent.name}")
        
        # Add workflow name
        if hasattr(run_config, "workflow_name"):
            attributes[WorkflowAttributes.WORKFLOW_NAME] = run_config.workflow_name
            
        return attributes

    def _add_agent_attributes_to_span(self, span, agent):
        """Add agent-specific attributes to the span."""
        # Add agent instructions
        if hasattr(agent, "instructions"):
            # Determine instruction type
            instruction_type = "unknown"
            if isinstance(agent.instructions, str):
                instruction_type = "string"
                span.set_attribute("agent.instructions", agent.instructions)
            elif callable(agent.instructions):
                instruction_type = "function"
                func_name = getattr(agent.instructions, "__name__", str(agent.instructions))
                span.set_attribute("agent.instruction_function", func_name)
            else:
                # Use safe_serialize for complex objects
                instructions_dict = model_to_dict(agent.instructions)
                span.set_attribute("agent.instructions", safe_serialize(instructions_dict))
            
            span.set_attribute("agent.instruction_type", instruction_type)
        
        # Add agent tools if available
        if hasattr(agent, "tools") and agent.tools:
            tool_names = [tool.name for tool in agent.tools if hasattr(tool, "name")]
            if tool_names:
                span.set_attribute(AgentAttributes.AGENT_TOOLS, ",".join(tool_names))
        
        # Add agent model settings if available
        if hasattr(agent, "model_settings") and agent.model_settings:
            # Add model settings directly using semantic conventions
            for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
                if hasattr(agent.model_settings, param) and getattr(agent.model_settings, param) is not None:
                    attr_name = getattr(SpanAttributes, f"LLM_REQUEST_{param.upper()}", f"gen_ai.request.{param}")
                    span.set_attribute(attr_name, getattr(agent.model_settings, param))

    def _process_result_and_update_span(self, span, result, model_name, start_time, is_streaming, agent_name):
        """Process the result and update the span with relevant information."""
        # Add result attributes to the span
        if hasattr(result, "final_output"):
            span.set_attribute(WorkflowAttributes.FINAL_OUTPUT, safe_serialize(result.final_output))
        
        # Process token usage from responses
        self._process_token_usage_from_responses(span, result, model_name)
        
        # Record execution time
        execution_time = time.time() - start_time  # In seconds
        self._record_execution_time(execution_time, model_name, agent_name, is_streaming)
        
        # Add instrumentation metadata
        self._add_instrumentation_metadata(span)

    def _process_token_usage_from_responses(self, span, result, model_name):
        """Process token usage information from responses and update the span."""
        if hasattr(result, "raw_responses") and result.raw_responses:
            total_input_tokens = 0
            total_output_tokens = 0
            total_tokens = 0
            total_reasoning_tokens = 0
            
            for i, response in enumerate(result.raw_responses):
                # Try to extract model directly
                if hasattr(response, "model"):
                    response_model = response.model
                    span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, response_model)
                
                # Extract usage information
                if hasattr(response, "usage"):
                    usage = response.usage
                    
                    # Handle input tokens
                    input_tokens = getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", 0))
                    if input_tokens:
                        span.set_attribute(f"{SpanAttributes.LLM_USAGE_PROMPT_TOKENS}.{i}", input_tokens)
                        total_input_tokens += input_tokens
                        
                        self._record_token_histogram(input_tokens, "input", model_name)
                    
                    # Handle output tokens
                    output_tokens = getattr(usage, "completion_tokens", getattr(usage, "output_tokens", 0))
                    if output_tokens:
                        span.set_attribute(f"{SpanAttributes.LLM_USAGE_COMPLETION_TOKENS}.{i}", output_tokens)
                        total_output_tokens += output_tokens
                        
                        self._record_token_histogram(output_tokens, "output", model_name)
                    
                    # Handle reasoning tokens if present
                    output_tokens_details = getattr(usage, "output_tokens_details", {})
                    if isinstance(output_tokens_details, dict):
                        reasoning_tokens = output_tokens_details.get("reasoning_tokens", 0)
                        if reasoning_tokens:
                            span.set_attribute(f"{SpanAttributes.LLM_USAGE_REASONING_TOKENS}.{i}", reasoning_tokens)
                            total_reasoning_tokens += reasoning_tokens
                            
                            self._record_token_histogram(reasoning_tokens, "reasoning", model_name)
                    
                    # Handle total tokens
                    if hasattr(usage, "total_tokens"):
                        span.set_attribute(f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.{i}", usage.total_tokens)
                        total_tokens += usage.total_tokens
            
            # Set total token counts on the span
            if total_input_tokens > 0:
                span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, total_input_tokens)
            
            if total_output_tokens > 0:
                span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, total_output_tokens)
            
            if total_reasoning_tokens > 0:
                span.set_attribute(SpanAttributes.LLM_USAGE_REASONING_TOKENS, total_reasoning_tokens)
            
            if total_tokens > 0:
                span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, total_tokens)

    def _record_token_histogram(self, token_count, token_type, model_name):
        """Record token usage in the histogram metric."""
        if self.__class__._agent_token_usage_histogram:
            self.__class__._agent_token_usage_histogram.record(
                token_count,
                {
                    "token_type": token_type,
                    "model": model_name,
                    SpanAttributes.LLM_REQUEST_MODEL: model_name,
                    SpanAttributes.LLM_SYSTEM: "openai",
                },
            )

    def _record_execution_time(self, execution_time, model_name, agent_name, is_streaming):
        """Record execution time in the histogram metric."""
        if self.__class__._agent_execution_time_histogram:
            # Create shared attributes following OpenAI conventions
            shared_attributes = {
                SpanAttributes.LLM_SYSTEM: "openai",
                "gen_ai.response.model": model_name,
                SpanAttributes.LLM_REQUEST_MODEL: model_name,
                "gen_ai.operation.name": "agent_run",
                "agent_name": agent_name,
                "stream": is_streaming,
            }
            
            self.__class__._agent_execution_time_histogram.record(
                execution_time, 
                attributes=shared_attributes
            )

    def _record_error_to_span(self, span, error):
        """Record an error to the span."""
        span.set_status(Status(StatusCode.ERROR))
        span.record_exception(error)
        span.set_attribute(CoreAttributes.ERROR_TYPE, type(error).__name__)
        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(error))

    def _add_instrumentation_metadata(self, span):
        """Add instrumentation metadata to the span."""
        span.set_attribute(InstrumentationAttributes.NAME, "agentops.agents")
        span.set_attribute(InstrumentationAttributes.VERSION, __version__)

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
