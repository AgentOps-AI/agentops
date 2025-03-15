import functools
import time
from typing import Any, Collection, Dict

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer, SpanKind, Status, StatusCode
from opentelemetry.metrics import get_meter

from agentops.semconv import (
    CoreAttributes,
    WorkflowAttributes,
    InstrumentationAttributes,
    AgentAttributes,
    SpanAttributes,
    MessageAttributes,
    Meters,
)
from agentops.logging import logger
from agentops.helpers.serialization import safe_serialize, model_to_dict
from agentops.instrumentation.openai_agents import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.openai_agents.exporter import OpenAIAgentsExporter
from agentops.instrumentation.openai_agents.processor import OpenAIAgentsProcessor


def get_model_info(agent: Any, run_config: Any = None) -> Dict[str, Any]:
    """Extract model information from agent and run_config."""
    result = {"model_name": "unknown"}

    if run_config and hasattr(run_config, "model") and run_config.model:
        if isinstance(run_config.model, str):
            result["model_name"] = run_config.model
        elif hasattr(run_config.model, "model") and run_config.model.model:
            result["model_name"] = run_config.model.model

    if result["model_name"] == "unknown" and hasattr(agent, "model") and agent.model:
        if isinstance(agent.model, str):
            result["model_name"] = agent.model
        elif hasattr(agent.model, "model") and agent.model.model:
            result["model_name"] = agent.model.model

    if result["model_name"] == "unknown":
        try:
            from agents.models.openai_provider import DEFAULT_MODEL
            result["model_name"] = DEFAULT_MODEL
        except ImportError:
            pass

    if hasattr(agent, "model_settings") and agent.model_settings:
        model_settings = agent.model_settings

        for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
            if hasattr(model_settings, param) and getattr(model_settings, param) is not None:
                result[param] = getattr(model_settings, param)

    if run_config and hasattr(run_config, "model_settings") and run_config.model_settings:
        model_settings = run_config.model_settings

        for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
            if hasattr(model_settings, param) and getattr(model_settings, param) is not None:
                result[param] = getattr(model_settings, param)

    return result

class AgentsInstrumentor(BaseInstrumentor):
    """An instrumentor for OpenAI Agents SDK."""
    
    _original_methods = {}
    _active_streaming_operations = set()
    _agent_run_counter = None
    _agent_execution_time_histogram = None
    _agent_token_usage_histogram = None

    def instrumentation_dependencies(self) -> Collection[str]:
        return ["openai-agents >= 0.0.1"]

    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get("tracer_provider")
        
        meter_provider = kwargs.get("meter_provider")
        if meter_provider:
            self._initialize_metrics(meter_provider)

        try:
            from agents import add_trace_processor
            
            processor = OpenAIAgentsProcessor()
            processor.exporter = OpenAIAgentsExporter(tracer_provider)
            add_trace_processor(processor)
        except Exception as e:
            logger.warning(f"Failed to add OpenAIAgentsProcessor: {e}")
        
        try:
            self._patch_runner_class(tracer_provider)
        except Exception as e:
            logger.warning(f"Failed to monkey patch Runner class: {e}")

    def _initialize_metrics(self, meter_provider):
        meter = get_meter(LIBRARY_NAME, LIBRARY_VERSION, meter_provider)
        
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
        from agents.run import Runner
        
        methods_to_patch = ["run_sync"]
        
        if hasattr(Runner, "run"):
            methods_to_patch.append("run")
        
        if hasattr(Runner, "run_streamed"):
            methods_to_patch.append("run_streamed")
        
        for method_name in methods_to_patch:
            if hasattr(Runner, method_name):
                self.__class__._original_methods[method_name] = getattr(Runner, method_name)
        
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
            
            tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider)
            
            model_info = get_model_info(starting_agent, run_config)
            model_name = model_info.get("model_name", "unknown")
            
            self._record_agent_run(starting_agent.name, "run_sync", "false", model_name)
            
            attributes = self._create_span_attributes(
                starting_agent, input, max_turns, model_name, "agents.run_sync", "false", model_info, run_config
            )
            
            with tracer.start_as_current_span(
                name=f"agents.run_sync.{starting_agent.name}", 
                kind=SpanKind.CLIENT, 
                attributes=attributes
            ) as span:
                self._add_agent_attributes_to_span(span, starting_agent)
                
                try:
                    original_method = self.__class__._original_methods["run_sync"]
                    result = original_method(
                        starting_agent,
                        input,
                        context=context,
                        max_turns=max_turns,
                        hooks=hooks,
                        run_config=run_config,
                    )
                    
                    self._process_result_and_update_span(
                        span, result, model_name, start_time, "false", starting_agent.name
                    )
                    
                    return result
                except Exception as e:
                    self._record_error_to_span(span, e)
                    raise
        
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
                
                tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider)
                
                model_info = get_model_info(starting_agent, run_config)
                model_name = model_info.get("model_name", "unknown")
                
                self._record_agent_run(starting_agent.name, "run", "false", model_name)
                
                attributes = self._create_span_attributes(
                    starting_agent, input, max_turns, model_name, "agents.run", "false", model_info, run_config
                )
                
                with tracer.start_as_current_span(
                    name=f"agents.run.{starting_agent.name}", 
                    kind=SpanKind.CLIENT, 
                    attributes=attributes
                ) as span:
                    self._add_agent_attributes_to_span(span, starting_agent)
                    
                    try:
                        original_method = self.__class__._original_methods["run"]
                        result = await original_method(
                            starting_agent,
                            input,
                            context=context,
                            max_turns=max_turns,
                            hooks=hooks,
                            run_config=run_config,
                        )
                        
                        self._process_result_and_update_span(
                            span, result, model_name, start_time, "false", starting_agent.name
                        )
                        
                        return result
                    except Exception as e:
                        self._record_error_to_span(span, e)
                        raise
        
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
                
                tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider)
                
                model_info = get_model_info(starting_agent, run_config)
                model_name = model_info.get("model_name", "unknown")
                
                self._record_agent_run(starting_agent.name, "run_streamed", "true", model_name)
                
                attributes = self._create_span_attributes(
                    starting_agent, input, max_turns, model_name, "agents.run_streamed", "true", model_info, run_config
                )
                
                with tracer.start_as_current_span(
                    name=f"agents.run_streamed.{starting_agent.name}", 
                    kind=SpanKind.CLIENT, 
                    attributes=attributes
                ) as span:
                    self._add_agent_attributes_to_span(span, starting_agent)
                    
                    try:
                        original_method = self.__class__._original_methods["run_streamed"]
                        result = original_method(
                            starting_agent,
                            input,
                            context=context,
                            max_turns=max_turns,
                            hooks=hooks,
                            run_config=run_config,
                        )
                        
                        self._instrument_streaming_result(
                            result, model_name, starting_agent.name, start_time, tracer_provider
                        )
                        
                        return result
                    except Exception as e:
                        self._record_error_to_span(span, e)
                        raise
        
        setattr(Runner, "run_sync", classmethod(instrumented_run_sync))
        
        if "run" in self.__class__._original_methods:
            setattr(Runner, "run", classmethod(instrumented_run))
        
        if "run_streamed" in self.__class__._original_methods:
            setattr(Runner, "run_streamed", classmethod(instrumented_run_streamed))

    def _instrument_streaming_result(self, result, model_name, agent_name, start_time, tracer_provider):
        stream_id = id(result)
        self.__class__._active_streaming_operations.add(stream_id)
        
        original_stream_events = result.stream_events
        
        @functools.wraps(original_stream_events)
        async def instrumented_stream_events():
            try:
                async for event in original_stream_events():
                    yield event
                
                self._process_streaming_completion(
                    result, model_name, agent_name, stream_id, start_time, tracer_provider
                )
                
            except Exception as e:
                logger.warning(f"Error in instrumented_stream_events: {e}")
            finally:
                if stream_id in self.__class__._active_streaming_operations:
                    self.__class__._active_streaming_operations.remove(stream_id)
        
        result.stream_events = instrumented_stream_events

    def _process_streaming_completion(self, result, model_name, agent_name, stream_id, start_time, tracer_provider):
        execution_time = time.time() - start_time
        
        usage_tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider)
        
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
        
        with usage_tracer.start_as_current_span(
            name=f"agents.run_streamed.usage.{agent_name}",
            kind=SpanKind.INTERNAL,
            attributes=usage_attributes,
        ) as usage_span:
            if hasattr(result, "final_output"):
                final_output = str(result.final_output)[:1000]
                usage_span.set_attribute(
                    WorkflowAttributes.FINAL_OUTPUT, final_output
                )
                # Also set the final output as the completion content using MessageAttributes
                usage_span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), final_output)
                usage_span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")
            
            self._process_token_usage_from_responses(usage_span, result, model_name)
            
            self._record_execution_time(execution_time, model_name, agent_name, "true")
            
            self._add_instrumentation_metadata(usage_span)

    def _record_agent_run(self, agent_name, method, is_streaming, model_name):
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
        
        for param, value in model_info.items():
            if param != "model_name":
                attributes[f"agent.model.{param}"] = value
        
        if run_config is None:
            from agents.run import RunConfig
            run_config = RunConfig(workflow_name=f"Agent {agent.name}")
        
        if hasattr(run_config, "workflow_name"):
            attributes[WorkflowAttributes.WORKFLOW_NAME] = run_config.workflow_name
            
        return attributes

    def _add_agent_attributes_to_span(self, span, agent):
        if hasattr(agent, "instructions"):
            instruction_type = "unknown"
            if isinstance(agent.instructions, str):
                instruction_type = "string"
                span.set_attribute("agent.instructions", agent.instructions)
                # Map agent instructions to gen_ai.prompt (LLM_PROMPTS)
                span.set_attribute(SpanAttributes.LLM_PROMPTS, agent.instructions)
            elif callable(agent.instructions):
                instruction_type = "function"
                func_name = getattr(agent.instructions, "__name__", str(agent.instructions))
                span.set_attribute("agent.instruction_function", func_name)
            else:
                instructions_dict = model_to_dict(agent.instructions)
                instructions_str = safe_serialize(instructions_dict)
                span.set_attribute("agent.instructions", instructions_str)
                # Map agent instructions to gen_ai.prompt (LLM_PROMPTS)
                span.set_attribute(SpanAttributes.LLM_PROMPTS, instructions_str)
            
            span.set_attribute("agent.instruction_type", instruction_type)
        
        if hasattr(agent, "tools") and agent.tools:
            tool_names = [tool.name for tool in agent.tools if hasattr(tool, "name")]
            if tool_names:
                span.set_attribute(AgentAttributes.AGENT_TOOLS, ",".join(tool_names))
        
        if hasattr(agent, "model_settings") and agent.model_settings:
            for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
                if hasattr(agent.model_settings, param) and getattr(agent.model_settings, param) is not None:
                    attr_name = getattr(SpanAttributes, f"LLM_REQUEST_{param.upper()}", f"gen_ai.request.{param}")
                    span.set_attribute(attr_name, getattr(agent.model_settings, param))

    def _process_result_and_update_span(self, span, result, model_name, start_time, is_streaming, agent_name):
        if hasattr(result, "final_output"):
            final_output = safe_serialize(result.final_output)
            span.set_attribute(WorkflowAttributes.FINAL_OUTPUT, final_output)
            
            # Also set the final output as the completion content using MessageAttributes
            span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), final_output)
            span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")
        
        self._process_token_usage_from_responses(span, result, model_name)
        
        execution_time = time.time() - start_time
        self._record_execution_time(execution_time, model_name, agent_name, is_streaming)
        
        self._add_instrumentation_metadata(span)

    def _process_token_usage_from_responses(self, span, result, model_name):
        if hasattr(result, "raw_responses") and result.raw_responses:
            total_input_tokens = 0
            total_output_tokens = 0
            total_tokens = 0
            total_reasoning_tokens = 0
            
            for i, response in enumerate(result.raw_responses):
                if hasattr(response, "model"):
                    response_model = response.model
                    span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, response_model)
                
                if hasattr(response, "usage"):
                    usage = response.usage
                    
                    input_tokens = getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", 0))
                    if input_tokens:
                        span.set_attribute(f"{SpanAttributes.LLM_USAGE_PROMPT_TOKENS}.{i}", input_tokens)
                        total_input_tokens += input_tokens
                        
                        self._record_token_histogram(input_tokens, "input", model_name)
                    
                    output_tokens = getattr(usage, "completion_tokens", getattr(usage, "output_tokens", 0))
                    if output_tokens:
                        span.set_attribute(f"{SpanAttributes.LLM_USAGE_COMPLETION_TOKENS}.{i}", output_tokens)
                        total_output_tokens += output_tokens
                        
                        self._record_token_histogram(output_tokens, "output", model_name)
                    
                    output_tokens_details = getattr(usage, "output_tokens_details", {})
                    if isinstance(output_tokens_details, dict):
                        reasoning_tokens = output_tokens_details.get("reasoning_tokens", 0)
                        if reasoning_tokens:
                            span.set_attribute(f"{SpanAttributes.LLM_USAGE_REASONING_TOKENS}.{i}", reasoning_tokens)
                            total_reasoning_tokens += reasoning_tokens
                            
                            self._record_token_histogram(reasoning_tokens, "reasoning", model_name)
                    
                    if hasattr(usage, "total_tokens"):
                        span.set_attribute(f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.{i}", usage.total_tokens)
                        total_tokens += usage.total_tokens
            
            if total_input_tokens > 0:
                span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, total_input_tokens)
            
            if total_output_tokens > 0:
                span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, total_output_tokens)
            
            if total_reasoning_tokens > 0:
                span.set_attribute(SpanAttributes.LLM_USAGE_REASONING_TOKENS, total_reasoning_tokens)
            
            if total_tokens > 0:
                span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, total_tokens)

    def _record_token_histogram(self, token_count, token_type, model_name):
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
        if self.__class__._agent_execution_time_histogram:
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
        span.set_status(Status(StatusCode.ERROR))
        span.record_exception(error)
        span.set_attribute(CoreAttributes.ERROR_TYPE, type(error).__name__)
        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(error))

    def _add_instrumentation_metadata(self, span):
        span.set_attribute(InstrumentationAttributes.NAME, "agentops.agents")
        span.set_attribute(InstrumentationAttributes.VERSION, LIBRARY_VERSION)

    def _uninstrument(self, **kwargs):
        try:
            from agents.run import Runner
            
            for method_name, original_method in self.__class__._original_methods.items():
                if hasattr(Runner, method_name):
                    setattr(Runner, method_name, original_method)
            
            self.__class__._original_methods.clear()
        except Exception as e:
            logger.warning(f"Failed to restore original Runner methods: {e}")
        
        self.__class__._active_streaming_operations.clear()
