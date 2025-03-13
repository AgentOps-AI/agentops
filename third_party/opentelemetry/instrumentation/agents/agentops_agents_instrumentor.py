"""
AgentOps Instrumentor for OpenAI Agents SDK

This module provides automatic instrumentation for the OpenAI Agents SDK when AgentOps is imported.
It combines a custom processor approach with monkey patching to capture all relevant spans and metrics.
"""

import asyncio
import functools
import inspect
import logging
import time
import json
import weakref
from typing import Any, Collection, Dict, List, Optional, Union, Set

# OpenTelemetry imports
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer, SpanKind, Status, StatusCode, get_current_span
from opentelemetry.metrics import get_meter

# AgentOps imports
from agentops.semconv import (
    CoreAttributes,
    WorkflowAttributes,
    InstrumentationAttributes,
    AgentAttributes,
    SpanAttributes,
    Meters,
)

# Agents SDK imports
from agents.tracing.processor_interface import TracingProcessor as AgentsTracingProcessor
from agents.tracing.spans import Span as AgentsSpan
from agents.tracing.traces import Trace as AgentsTrace
from agents import add_trace_processor
from agents.run import RunConfig
from agents.lifecycle import RunHooks

# Version
__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# Global metrics objects
_agent_run_counter = None
_agent_turn_counter = None
_agent_execution_time_histogram = None
_agent_token_usage_histogram = None

# Keep track of active streaming operations to prevent premature shutdown
_active_streaming_operations = set()


def safe_execute(func):
    """Decorator to safely execute a function and log any exceptions."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Error in {func.__name__}: {e}")
            return None

    return wrapper


@safe_execute
def get_model_info(agent: Any, run_config: Any = None) -> Dict[str, Any]:
    """Extract model information from agent and run_config."""

    result = {"model_name": "unknown"}

    # First check run_config.model (highest priority)
    if run_config and hasattr(run_config, "model") and run_config.model:
        if isinstance(run_config.model, str):
            result["model_name"] = run_config.model
        elif hasattr(run_config.model, "model") and run_config.model.model:
            # For Model objects that have a model attribute
            result["model_name"] = run_config.model.model

    # Then check agent.model if we still have unknown
    if result["model_name"] == "unknown" and hasattr(agent, "model") and agent.model:
        if isinstance(agent.model, str):
            result["model_name"] = agent.model
        elif hasattr(agent.model, "model") and agent.model.model:
            # For Model objects that have a model attribute
            result["model_name"] = agent.model.model

    # Check for default model from OpenAI provider
    if result["model_name"] == "unknown":
        # Try to import the default model from the SDK
        try:
            from agents.models.openai_provider import DEFAULT_MODEL

            result["model_name"] = DEFAULT_MODEL
        except ImportError:
            pass

    # Extract model settings from agent
    if hasattr(agent, "model_settings") and agent.model_settings:
        model_settings = agent.model_settings

        # Extract model parameters
        for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
            if hasattr(model_settings, param) and getattr(model_settings, param) is not None:
                result[param] = getattr(model_settings, param)

    # Override with run_config.model_settings if available
    if run_config and hasattr(run_config, "model_settings") and run_config.model_settings:
        model_settings = run_config.model_settings

        # Extract model parameters
        for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
            if hasattr(model_settings, param) and getattr(model_settings, param) is not None:
                result[param] = getattr(model_settings, param)

    return result


class AgentsDetailedExporter:
    """
    A detailed exporter for Agents SDK traces and spans that forwards them to AgentOps.
    """

    def __init__(self, tracer_provider=None):
        self.tracer_provider = tracer_provider

    def export(self, items: list[Union[AgentsTrace, AgentsSpan[Any]]]) -> None:
        """Export Agents SDK traces and spans to AgentOps."""
        for item in items:
            if isinstance(item, AgentsTrace):
                self._export_trace(item)
            else:
                self._export_span(item)

    def _export_trace(self, trace: AgentsTrace) -> None:
        """Export an Agents SDK trace to AgentOps."""
        # Get the current tracer
        tracer = get_tracer("agents-sdk", __version__, self.tracer_provider)

        # Create a new span for the trace
        with tracer.start_as_current_span(
            name=f"agents.trace.{trace.name}",
            kind=SpanKind.INTERNAL,
            attributes={
                WorkflowAttributes.WORKFLOW_NAME: trace.name,
                CoreAttributes.TRACE_ID: trace.trace_id,
                InstrumentationAttributes.LIBRARY_NAME: "agents-sdk",
                InstrumentationAttributes.LIBRARY_VERSION: __version__,
                WorkflowAttributes.WORKFLOW_STEP_TYPE: "trace",
            },
        ) as span:
            # Add any additional attributes from the trace
            if hasattr(trace, "group_id") and trace.group_id:
                span.set_attribute(CoreAttributes.GROUP_ID, trace.group_id)

    def _export_span(self, span: AgentsSpan[Any]) -> None:
        """Export an Agents SDK span to AgentOps."""
        # Get the current tracer
        tracer = get_tracer("agents-sdk", __version__, self.tracer_provider)

        # Determine span name and kind based on span data type
        span_data = span.span_data
        span_type = span_data.__class__.__name__.replace("SpanData", "")

        # Map span types to appropriate attributes
        attributes = {
            CoreAttributes.TRACE_ID: span.trace_id,
            CoreAttributes.SPAN_ID: span.span_id,
            InstrumentationAttributes.LIBRARY_NAME: "agents-sdk",
            InstrumentationAttributes.LIBRARY_VERSION: __version__,
        }

        # Add parent ID if available
        if span.parent_id:
            attributes[CoreAttributes.PARENT_ID] = span.parent_id

        # Add span-specific attributes
        if hasattr(span_data, "name"):
            attributes[AgentAttributes.AGENT_NAME] = span_data.name

        if hasattr(span_data, "input") and span_data.input:
            attributes[SpanAttributes.LLM_PROMPTS] = str(span_data.input)[:1000]  # Truncate long inputs

        if hasattr(span_data, "output") and span_data.output:
            attributes[SpanAttributes.LLM_COMPLETIONS] = str(span_data.output)[:1000]  # Truncate long outputs

        # Extract model information - check for GenerationSpanData specifically
        if span_type == "Generation" and hasattr(span_data, "model") and span_data.model:
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = span_data.model
            attributes["gen_ai.request.model"] = span_data.model  # Standard OpenTelemetry attribute
            attributes["gen_ai.system"] = "openai"  # Standard OpenTelemetry attribute

            # Add model config if available
            if hasattr(span_data, "model_config") and span_data.model_config:
                for key, value in span_data.model_config.items():
                    attributes[f"agent.model.{key}"] = value

        # Record token usage metrics if available
        if hasattr(span_data, "usage") and span_data.usage and isinstance(span_data.usage, dict):
            # Record token usage metrics if available
            if _agent_token_usage_histogram:
                if "prompt_tokens" in span_data.usage:
                    _agent_token_usage_histogram.record(
                        span_data.usage["prompt_tokens"],
                        {
                            "token_type": "input",
                            "model": attributes.get(SpanAttributes.LLM_REQUEST_MODEL, "unknown"),
                            "gen_ai.request.model": attributes.get(SpanAttributes.LLM_REQUEST_MODEL, "unknown"),
                            "gen_ai.system": "openai",
                        },
                    )
                    attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = span_data.usage["prompt_tokens"]

                if "completion_tokens" in span_data.usage:
                    _agent_token_usage_histogram.record(
                        span_data.usage["completion_tokens"],
                        {
                            "token_type": "output",
                            "model": attributes.get(SpanAttributes.LLM_REQUEST_MODEL, "unknown"),
                            "gen_ai.request.model": attributes.get(SpanAttributes.LLM_REQUEST_MODEL, "unknown"),
                            "gen_ai.system": "openai",
                        },
                    )
                    attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = span_data.usage["completion_tokens"]

                if "total_tokens" in span_data.usage:
                    attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = span_data.usage["total_tokens"]

        if hasattr(span_data, "from_agent") and span_data.from_agent:
            attributes[AgentAttributes.FROM_AGENT] = span_data.from_agent

        if hasattr(span_data, "to_agent") and span_data.to_agent:
            attributes[AgentAttributes.TO_AGENT] = span_data.to_agent

        if hasattr(span_data, "tools") and span_data.tools:
            attributes[AgentAttributes.TOOLS] = ",".join(span_data.tools)

        if hasattr(span_data, "handoffs") and span_data.handoffs:
            attributes[AgentAttributes.HANDOFFS] = ",".join(span_data.handoffs)

        # Create a span with the appropriate name and attributes
        span_name = f"agents.{span_type.lower()}"

        # Determine span kind based on span type
        span_kind = SpanKind.INTERNAL
        if span_type == "Agent":
            span_kind = SpanKind.CONSUMER
        elif span_type == "Function":
            span_kind = SpanKind.CLIENT
        elif span_type == "Generation":
            span_kind = SpanKind.CLIENT

        # Create the span
        with tracer.start_as_current_span(name=span_name, kind=span_kind, attributes=attributes) as otel_span:
            # Add error information if available
            if hasattr(span, "error") and span.error:
                otel_span.set_status(Status(StatusCode.ERROR))
                otel_span.record_exception(
                    exception=Exception(span.error.get("message", "Unknown error")),
                    attributes={"error.data": json.dumps(span.error.get("data", {}))},
                )


class AgentsDetailedProcessor(AgentsTracingProcessor):
    """
    A processor for Agents SDK traces and spans that forwards them to AgentOps.
    """

    def __init__(self):
        self.exporter = AgentsDetailedExporter(None)

    def on_trace_start(self, trace: AgentsTrace) -> None:
        self.exporter.export([trace])

    def on_trace_end(self, trace: AgentsTrace) -> None:
        self.exporter.export([trace])

    def on_span_start(self, span: AgentsSpan[Any]) -> None:
        self.exporter.export([span])

    def on_span_end(self, span: AgentsSpan[Any]) -> None:
        """Process a span when it ends."""
        # Log the span type for debugging
        span_type = span.span_data.__class__.__name__.replace("SpanData", "")

        self.exporter.export([span])

    def shutdown(self) -> None:
        pass

    def force_flush(self):
        pass


class AgentsInstrumentor(BaseInstrumentor):
    """An instrumentor for OpenAI Agents SDK."""

    def instrumentation_dependencies(self) -> Collection[str]:
        return ["openai-agents >= 0.0.1"]

    def _instrument(self, **kwargs):
        """Instrument the Agents SDK."""
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(
            __name__,
            __version__,
            tracer_provider,
        )

        global _agent_run_counter, _agent_turn_counter, _agent_execution_time_histogram, _agent_token_usage_histogram
        meter_provider = kwargs.get("meter_provider")
        if meter_provider:
            meter = get_meter(__name__, __version__, meter_provider)

            _agent_run_counter = meter.create_counter(name="agents.runs", unit="run", description="Counts agent runs")

            _agent_turn_counter = meter.create_counter(
                name="agents.turns", unit="turn", description="Counts agent turns"
            )

            _agent_execution_time_histogram = meter.create_histogram(
                name=Meters.LLM_OPERATION_DURATION, unit="s", description="GenAI operation duration"
            )

            _agent_token_usage_histogram = meter.create_histogram(
                name=Meters.LLM_TOKEN_USAGE, unit="token", description="Measures token usage in agent runs"
            )

        # Try to import the default model from the SDK for reference
        try:
            from agents.models.openai_provider import DEFAULT_MODEL
        except ImportError:
            pass

        # Add the custom processor to the Agents SDK
        try:
            from agents import add_trace_processor

            processor = AgentsDetailedProcessor()
            processor.exporter = AgentsDetailedExporter(tracer_provider)
            add_trace_processor(processor)
        except Exception as e:
            logger.warning(f"Failed to add AgentsDetailedProcessor: {e}")
            pass

        # Monkey patch the Runner class
        try:
            self._patch_runner_class(tracer_provider)
        except Exception as e:
            logger.warning(f"Failed to monkey patch Runner class: {e}")
            pass

    def _patch_runner_class(self, tracer_provider):
        """Monkey patch the Runner class to capture additional information."""
        from agents.run import Runner

        # Store original methods
        original_methods = {
            "run": Runner.run,
            "run_sync": Runner.run_sync,
            "run_streamed": Runner.run_streamed if hasattr(Runner, "run_streamed") else None,
        }

        # Filter out None values
        original_methods = {k: v for k, v in original_methods.items() if v is not None}

        # Create instrumented versions of each method
        for method_name, original_method in original_methods.items():
            is_async = method_name in ["run", "run_streamed"]

            if method_name == "run_streamed":

                @functools.wraps(original_method)
                def instrumented_run_streamed(
                    cls,
                    starting_agent,
                    input,
                    context=None,
                    max_turns=10,
                    hooks=None,
                    run_config=None,
                    _original=original_method,
                    _tracer_provider=tracer_provider,
                ):
                    start_time = time.time()

                    # Get the current tracer
                    tracer = get_tracer(__name__, __version__, _tracer_provider)

                    # Extract model information from agent and run_config
                    model_info = get_model_info(starting_agent, run_config)
                    model_name = model_info.get("model_name", "unknown")
                    logger.warning(f"[DEBUG] Extracted model name for streaming: {model_name}")

                    # Record agent run counter
                    if _agent_run_counter:
                        _agent_run_counter.add(
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
                        "agent.name": starting_agent.name,
                        WorkflowAttributes.WORKFLOW_INPUT: str(input)[:1000],
                        WorkflowAttributes.MAX_TURNS: max_turns,
                        "service.name": "agentops.agents",
                        WorkflowAttributes.WORKFLOW_TYPE: "agents.run_streamed",
                        SpanAttributes.LLM_REQUEST_MODEL: model_name,
                        "gen_ai.request.model": model_name,  # Standard OpenTelemetry attribute
                        "gen_ai.system": "openai",  # Standard OpenTelemetry attribute
                        "stream": "true",
                    }

                    # Add model parameters from model_info
                    for param, value in model_info.items():
                        if param != "model_name":
                            attributes[f"agent.model.{param}"] = value

                    # Create a default RunConfig if None is provided
                    if run_config is None:
                        run_config = RunConfig(workflow_name=f"Agent {starting_agent.name}")

                    if hasattr(run_config, "workflow_name"):
                        attributes[WorkflowAttributes.WORKFLOW_NAME] = run_config.workflow_name

                    # Create default hooks if None is provided
                    if hooks is None:
                        hooks = RunHooks()

                    # Start a span for the run
                    with tracer.start_as_current_span(
                        name=f"agents.run_streamed.{starting_agent.name}", kind=SpanKind.CLIENT, attributes=attributes
                    ) as span:
                        # Add agent attributes
                        if hasattr(starting_agent, "instructions"):
                            # Determine instruction type
                            instruction_type = "unknown"
                            if isinstance(starting_agent.instructions, str):
                                instruction_type = "string"
                                span.set_attribute("agent.instructions", starting_agent.instructions[:1000])
                            elif callable(starting_agent.instructions):
                                instruction_type = "function"
                                # Store the function name or representation
                                func_name = getattr(
                                    starting_agent.instructions, "__name__", str(starting_agent.instructions)
                                )
                                span.set_attribute("agent.instruction_function", func_name)
                            else:
                                span.set_attribute("agent.instructions", str(starting_agent.instructions)[:1000])

                            span.set_attribute("agent.instruction_type", instruction_type)

                        # Add agent tools if available
                        if hasattr(starting_agent, "tools") and starting_agent.tools:
                            tool_names = [tool.name for tool in starting_agent.tools if hasattr(tool, "name")]
                            if tool_names:
                                span.set_attribute(AgentAttributes.AGENT_TOOLS, str(tool_names))

                        # Add agent model settings if available
                        if hasattr(starting_agent, "model_settings") and starting_agent.model_settings:
                            # Add model settings directly
                            if (
                                hasattr(starting_agent.model_settings, "temperature")
                                and starting_agent.model_settings.temperature is not None
                            ):
                                span.set_attribute(
                                    SpanAttributes.LLM_REQUEST_TEMPERATURE, starting_agent.model_settings.temperature
                                )

                            if (
                                hasattr(starting_agent.model_settings, "top_p")
                                and starting_agent.model_settings.top_p is not None
                            ):
                                span.set_attribute(
                                    SpanAttributes.LLM_REQUEST_TOP_P, starting_agent.model_settings.top_p
                                )

                            if (
                                hasattr(starting_agent.model_settings, "frequency_penalty")
                                and starting_agent.model_settings.frequency_penalty is not None
                            ):
                                span.set_attribute(
                                    SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY,
                                    starting_agent.model_settings.frequency_penalty,
                                )

                            if (
                                hasattr(starting_agent.model_settings, "presence_penalty")
                                and starting_agent.model_settings.presence_penalty is not None
                            ):
                                span.set_attribute(
                                    SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY,
                                    starting_agent.model_settings.presence_penalty,
                                )

                        try:
                            # Execute the original method WITHOUT awaiting it
                            # This returns a RunResultStreaming object
                            result = _original(
                                starting_agent,
                                input,
                                context=context,
                                max_turns=max_turns,
                                hooks=hooks,
                                run_config=run_config,
                            )

                            # Create a unique identifier for this streaming operation
                            stream_id = id(result)

                            # Add this streaming operation to the active set
                            global _active_streaming_operations
                            _active_streaming_operations.add(stream_id)
                            logger.warning(
                                f"[DEBUG] Added streaming operation {stream_id} to active set. Current active: {len(_active_streaming_operations)}"
                            )

                            # Create a wrapper for the stream_events method to capture metrics after streaming
                            original_stream_events = result.stream_events

                            @functools.wraps(original_stream_events)
                            async def instrumented_stream_events():
                                # Capture model_name from outer scope to make it available in this function
                                nonlocal model_name

                                try:
                                    # Use the original stream_events method
                                    async for event in original_stream_events():
                                        yield event

                                    # After streaming is complete, capture metrics
                                    # This runs after all events have been streamed
                                    execution_time = time.time() - start_time  # In seconds

                                    # Log the entire result object for debugging
                                    logger.warning(f"[DEBUG] Streaming complete, result object: {result}")

                                    # Log all attributes of the result object
                                    logger.warning("[DEBUG] RunResultStreaming attributes:")
                                    for attr_name in dir(result):
                                        if not attr_name.startswith("_") and not callable(getattr(result, attr_name)):
                                            logger.warning(f"[DEBUG]   {attr_name}: {getattr(result, attr_name)}")

                                    # Create a new span specifically for token usage metrics
                                    # This ensures we have a fresh span that won't be closed prematurely
                                    logger.warning(
                                        f"[DEBUG] Creating new span for token usage metrics for streaming operation {stream_id}"
                                    )

                                    # Get the current trace context
                                    current_span = get_current_span()
                                    current_trace_id = None
                                    current_span_id = None

                                    # Extract trace ID and span ID from current span if available
                                    if hasattr(current_span, "get_span_context"):
                                        span_context = current_span.get_span_context()
                                        if hasattr(span_context, "trace_id"):
                                            current_trace_id = span_context.trace_id
                                            logger.warning(f"[DEBUG] Current trace ID: {current_trace_id}")
                                        if hasattr(span_context, "span_id"):
                                            current_span_id = span_context.span_id
                                            logger.warning(f"[DEBUG] Current span ID: {current_span_id}")

                                    # Get a new tracer
                                    usage_tracer = get_tracer(__name__, __version__, _tracer_provider)

                                    # Create attributes for the new span
                                    usage_attributes = {
                                        "span.kind": SpanKind.INTERNAL,
                                        "agent.name": starting_agent.name,
                                        "service.name": "agentops.agents",
                                        WorkflowAttributes.WORKFLOW_TYPE: "agents.run_streamed.usage",
                                        SpanAttributes.LLM_REQUEST_MODEL: model_name,
                                        "gen_ai.request.model": model_name,
                                        "gen_ai.system": "openai",
                                        "stream": "true",
                                        "stream_id": str(stream_id),
                                    }

                                    # Add trace ID if available to ensure same trace
                                    if current_trace_id:
                                        usage_attributes[CoreAttributes.TRACE_ID] = current_trace_id

                                    # Add parent span ID if available
                                    if current_span_id:
                                        usage_attributes[CoreAttributes.PARENT_ID] = current_span_id

                                    # Add workflow name if available
                                    if hasattr(run_config, "workflow_name"):
                                        usage_attributes[WorkflowAttributes.WORKFLOW_NAME] = run_config.workflow_name

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

                                        # Extract model and response information
                                        response_id = None

                                        # Process raw responses
                                        if hasattr(result, "raw_responses") and result.raw_responses:
                                            logger.warning(
                                                f"[DEBUG] Found raw_responses in streaming result: {len(result.raw_responses)}"
                                            )
                                            total_input_tokens = 0
                                            total_output_tokens = 0
                                            total_tokens = 0

                                            # Log detailed information about each raw response
                                            for i, response in enumerate(result.raw_responses):
                                                logger.warning(
                                                    f"[DEBUG] Processing streaming raw_response {i}: {type(response).__name__}"
                                                )

                                                # Log all attributes of the response object
                                                logger.warning(f"[DEBUG] Raw response {i} attributes:")
                                                for attr_name in dir(response):
                                                    if not attr_name.startswith("_") and not callable(
                                                        getattr(response, attr_name)
                                                    ):
                                                        logger.warning(
                                                            f"[DEBUG]   {attr_name}: {getattr(response, attr_name)}"
                                                        )

                                                # Try to extract model directly
                                                if hasattr(response, "model"):
                                                    model_name = response.model
                                                    logger.warning(
                                                        f"[DEBUG] Found model in streaming raw_response: {model_name}"
                                                    )
                                                    usage_span.set_attribute(
                                                        SpanAttributes.LLM_REQUEST_MODEL, model_name
                                                    )

                                                # Extract response ID if available
                                                if hasattr(response, "referenceable_id") and response.referenceable_id:
                                                    response_id = response.referenceable_id
                                                    logger.warning(
                                                        f"[DEBUG] Found streaming response_id: {response_id}"
                                                    )
                                                    usage_span.set_attribute(f"gen_ai.response.id.{i}", response_id)

                                                # Extract usage information
                                                if hasattr(response, "usage"):
                                                    usage = response.usage
                                                    logger.warning(f"[DEBUG] Found streaming usage: {usage}")

                                                    # Add token usage
                                                    if hasattr(usage, "prompt_tokens") or hasattr(
                                                        usage, "input_tokens"
                                                    ):
                                                        input_tokens = getattr(
                                                            usage, "prompt_tokens", getattr(usage, "input_tokens", 0)
                                                        )
                                                        usage_span.set_attribute(
                                                            f"{SpanAttributes.LLM_USAGE_PROMPT_TOKENS}.{i}",
                                                            input_tokens,
                                                        )
                                                        total_input_tokens += input_tokens

                                                        if _agent_token_usage_histogram:
                                                            _agent_token_usage_histogram.record(
                                                                input_tokens,
                                                                {
                                                                    "token_type": "input",
                                                                    "model": model_name,
                                                                    "gen_ai.request.model": model_name,
                                                                    "gen_ai.system": "openai",
                                                                },
                                                            )

                                                    if hasattr(usage, "completion_tokens") or hasattr(
                                                        usage, "output_tokens"
                                                    ):
                                                        output_tokens = getattr(
                                                            usage,
                                                            "completion_tokens",
                                                            getattr(usage, "output_tokens", 0),
                                                        )
                                                        usage_span.set_attribute(
                                                            f"{SpanAttributes.LLM_USAGE_COMPLETION_TOKENS}.{i}",
                                                            output_tokens,
                                                        )
                                                        total_output_tokens += output_tokens

                                                        if _agent_token_usage_histogram:
                                                            _agent_token_usage_histogram.record(
                                                                output_tokens,
                                                                {
                                                                    "token_type": "output",
                                                                    "model": model_name,
                                                                    "gen_ai.request.model": model_name,
                                                                    "gen_ai.system": "openai",
                                                                },
                                                            )

                                                    if hasattr(usage, "total_tokens"):
                                                        usage_span.set_attribute(
                                                            f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.{i}",
                                                            usage.total_tokens,
                                                        )
                                                        total_tokens += usage.total_tokens
                                                else:
                                                    logger.warning(
                                                        f"[DEBUG] No usage attribute found in response {i}, checking for other token usage information"
                                                    )
                                                    # Try to find token usage information in other attributes
                                                    for attr_name in dir(response):
                                                        if not attr_name.startswith("_") and not callable(
                                                            getattr(response, attr_name)
                                                        ):
                                                            attr_value = getattr(response, attr_name)
                                                            if isinstance(attr_value, dict) and (
                                                                "tokens" in str(attr_value).lower()
                                                                or "usage" in str(attr_value).lower()
                                                            ):
                                                                logger.warning(
                                                                    f"[DEBUG] Potential token usage information found in attribute {attr_name}: {attr_value}"
                                                                )
                                                            elif hasattr(attr_value, "usage"):
                                                                logger.warning(
                                                                    f"[DEBUG] Found nested usage attribute in {attr_name}: {getattr(attr_value, 'usage')}"
                                                                )
                                                                # Process this nested usage attribute if needed

                                            # Set total token counts
                                            if total_input_tokens > 0:
                                                usage_span.set_attribute(
                                                    SpanAttributes.LLM_USAGE_PROMPT_TOKENS, total_input_tokens
                                                )

                                            if total_output_tokens > 0:
                                                usage_span.set_attribute(
                                                    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, total_output_tokens
                                                )

                                            if total_tokens > 0:
                                                usage_span.set_attribute(
                                                    SpanAttributes.LLM_USAGE_TOTAL_TOKENS, total_tokens
                                                )

                                        # Record execution time
                                        if _agent_execution_time_histogram:
                                            # Create shared attributes following OpenAI conventions
                                            shared_attributes = {
                                                "gen_ai.system": "openai",
                                                "gen_ai.response.model": model_name,
                                                "gen_ai.request.model": model_name,  # Standard OpenTelemetry attribute
                                                "gen_ai.operation.name": "agent_run",
                                                "agent_name": starting_agent.name,
                                                "stream": "true",
                                            }

                                            # Add response ID if available
                                            if response_id:
                                                shared_attributes["gen_ai.response.id"] = response_id

                                            logger.warning(
                                                f"[DEBUG] Final streaming metrics attributes: {shared_attributes}"
                                            )

                                            _agent_execution_time_histogram.record(
                                                execution_time, attributes=shared_attributes
                                            )

                                        # Add instrumentation metadata
                                        usage_span.set_attribute(InstrumentationAttributes.NAME, "agentops.agents")
                                        usage_span.set_attribute(InstrumentationAttributes.VERSION, __version__)

                                        # Force flush the span to ensure metrics are recorded
                                        logger.warning(
                                            f"[DEBUG] Forcing flush of usage span for streaming operation {stream_id}"
                                        )
                                        if hasattr(tracer_provider, "force_flush"):
                                            try:
                                                tracer_provider.force_flush()
                                                logger.warning(
                                                    f"[DEBUG] Successfully flushed usage span for streaming operation {stream_id}"
                                                )
                                            except Exception as e:
                                                logger.warning(
                                                    f"[DEBUG] Error flushing usage span for streaming operation {stream_id}: {e}"
                                                )

                                except Exception as e:
                                    # Record the error
                                    logger.warning(f"[ERROR] Error in instrumented_stream_events: {e}")
                                    # Don't re-raise the exception to avoid breaking the streaming
                                finally:
                                    # Remove this streaming operation from the active set
                                    if stream_id in _active_streaming_operations:
                                        _active_streaming_operations.remove(stream_id)
                                        logger.warning(
                                            f"[DEBUG] Removed streaming operation {stream_id} from active set. Remaining active: {len(_active_streaming_operations)}"
                                        )

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

                setattr(Runner, method_name, classmethod(instrumented_run_streamed))
            elif is_async:

                @functools.wraps(original_method)
                async def instrumented_method(
                    cls,
                    starting_agent,
                    input,
                    context=None,
                    max_turns=10,
                    hooks=None,
                    run_config=None,
                    _method_name=method_name,
                    _original=original_method,
                    _tracer_provider=tracer_provider,
                ):
                    start_time = time.time()

                    # Get the current tracer
                    tracer = get_tracer(__name__, __version__, _tracer_provider)

                    # Extract model information from agent and run_config
                    model_info = get_model_info(starting_agent, run_config)
                    model_name = model_info.get("model_name", "unknown")
                    logger.warning(f"[DEBUG] Extracted model name: {model_name}")

                    # Record agent run counter
                    if _agent_run_counter:
                        _agent_run_counter.add(
                            1,
                            {
                                "agent_name": starting_agent.name,
                                "method": _method_name,
                                "stream": "false",
                                "model": model_name,
                            },
                        )

                    # Create span attributes
                    attributes = {
                        "span.kind": WorkflowAttributes.WORKFLOW_STEP,
                        "agent.name": starting_agent.name,
                        WorkflowAttributes.WORKFLOW_INPUT: str(input)[:1000],
                        WorkflowAttributes.MAX_TURNS: max_turns,
                        "service.name": "agentops.agents",
                        WorkflowAttributes.WORKFLOW_TYPE: f"agents.{_method_name}",
                        SpanAttributes.LLM_REQUEST_MODEL: model_name,
                        "gen_ai.request.model": model_name,  # Standard OpenTelemetry attribute
                        "gen_ai.system": "openai",  # Standard OpenTelemetry attribute
                        "stream": "false",
                    }

                    # Add model parameters from model_info
                    for param, value in model_info.items():
                        if param != "model_name":
                            attributes[f"agent.model.{param}"] = value

                    # Create a default RunConfig if None is provided
                    if run_config is None:
                        run_config = RunConfig(workflow_name=f"Agent {starting_agent.name}")

                    if hasattr(run_config, "workflow_name"):
                        attributes[WorkflowAttributes.WORKFLOW_NAME] = run_config.workflow_name

                    # Create default hooks if None is provided
                    if hooks is None:
                        hooks = RunHooks()

                    # Start a span for the run
                    with tracer.start_as_current_span(
                        name=f"agents.{_method_name}.{starting_agent.name}", kind=SpanKind.CLIENT, attributes=attributes
                    ) as span:
                        # Add agent attributes
                        if hasattr(starting_agent, "instructions"):
                            # Determine instruction type
                            instruction_type = "unknown"
                            if isinstance(starting_agent.instructions, str):
                                instruction_type = "string"
                                span.set_attribute("agent.instructions", starting_agent.instructions[:1000])
                            elif callable(starting_agent.instructions):
                                instruction_type = "function"
                                # Store the function name or representation
                                func_name = getattr(
                                    starting_agent.instructions, "__name__", str(starting_agent.instructions)
                                )
                                span.set_attribute("agent.instruction_function", func_name)
                            else:
                                span.set_attribute("agent.instructions", str(starting_agent.instructions)[:1000])

                            span.set_attribute("agent.instruction_type", instruction_type)

                        # Add agent tools if available
                        if hasattr(starting_agent, "tools") and starting_agent.tools:
                            tool_names = [tool.name for tool in starting_agent.tools if hasattr(tool, "name")]
                            if tool_names:
                                span.set_attribute(AgentAttributes.AGENT_TOOLS, str(tool_names))

                        # Add agent model settings if available
                        if hasattr(starting_agent, "model_settings") and starting_agent.model_settings:
                            # Add model settings directly
                            if (
                                hasattr(starting_agent.model_settings, "temperature")
                                and starting_agent.model_settings.temperature is not None
                            ):
                                span.set_attribute(
                                    SpanAttributes.LLM_REQUEST_TEMPERATURE, starting_agent.model_settings.temperature
                                )

                            if (
                                hasattr(starting_agent.model_settings, "top_p")
                                and starting_agent.model_settings.top_p is not None
                            ):
                                span.set_attribute(
                                    SpanAttributes.LLM_REQUEST_TOP_P, starting_agent.model_settings.top_p
                                )

                            if (
                                hasattr(starting_agent.model_settings, "frequency_penalty")
                                and starting_agent.model_settings.frequency_penalty is not None
                            ):
                                span.set_attribute(
                                    SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY,
                                    starting_agent.model_settings.frequency_penalty,
                                )

                            if (
                                hasattr(starting_agent.model_settings, "presence_penalty")
                                and starting_agent.model_settings.presence_penalty is not None
                            ):
                                span.set_attribute(
                                    SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY,
                                    starting_agent.model_settings.presence_penalty,
                                )

                        try:
                            # Execute the original method with keyword arguments
                            result = await _original(
                                starting_agent,
                                input,
                                context=context,
                                max_turns=max_turns,
                                hooks=hooks,
                                run_config=run_config,
                            )

                            # Add result attributes to the span
                            if hasattr(result, "final_output"):
                                span.set_attribute(WorkflowAttributes.FINAL_OUTPUT, str(result.final_output)[:1000])

                            # Extract model and response information
                            response_id = None

                            # Process raw responses
                            if hasattr(result, "raw_responses") and result.raw_responses:
                                logger.warning(f"[DEBUG] Found raw_responses: {len(result.raw_responses)}")
                                total_input_tokens = 0
                                total_output_tokens = 0
                                total_tokens = 0

                                for i, response in enumerate(result.raw_responses):
                                    logger.warning(f"[DEBUG] Processing raw_response {i}: {type(response).__name__}")

                                    # Try to extract model directly
                                    if hasattr(response, "model"):
                                        model_name = response.model
                                        logger.warning(f"[DEBUG] Found model in raw_response: {model_name}")
                                        span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, model_name)

                                    # Extract response ID if available
                                    if hasattr(response, "referenceable_id") and response.referenceable_id:
                                        response_id = response.referenceable_id
                                        logger.warning(f"[DEBUG] Found response_id: {response_id}")
                                        span.set_attribute(f"gen_ai.response.id.{i}", response_id)

                                    # Extract usage information
                                    if hasattr(response, "usage"):
                                        usage = response.usage
                                        logger.warning(f"[DEBUG] Found usage: {usage}")

                                        # Add token usage
                                        if hasattr(usage, "prompt_tokens") or hasattr(usage, "input_tokens"):
                                            input_tokens = getattr(
                                                usage, "prompt_tokens", getattr(usage, "input_tokens", 0)
                                            )
                                            span.set_attribute(
                                                f"{SpanAttributes.LLM_USAGE_PROMPT_TOKENS}.{i}", input_tokens
                                            )
                                            total_input_tokens += input_tokens

                                            if _agent_token_usage_histogram:
                                                _agent_token_usage_histogram.record(
                                                    input_tokens,
                                                    {
                                                        "token_type": "input",
                                                        "model": model_name,
                                                        "gen_ai.request.model": model_name,
                                                        "gen_ai.system": "openai",
                                                    },
                                                )

                                        if hasattr(usage, "completion_tokens") or hasattr(usage, "output_tokens"):
                                            output_tokens = getattr(
                                                usage, "completion_tokens", getattr(usage, "output_tokens", 0)
                                            )
                                            span.set_attribute(
                                                f"{SpanAttributes.LLM_USAGE_COMPLETION_TOKENS}.{i}", output_tokens
                                            )
                                            total_output_tokens += output_tokens

                                            if _agent_token_usage_histogram:
                                                _agent_token_usage_histogram.record(
                                                    output_tokens,
                                                    {
                                                        "token_type": "output",
                                                        "model": model_name,
                                                        "gen_ai.request.model": model_name,
                                                        "gen_ai.system": "openai",
                                                    },
                                                )

                                        if hasattr(usage, "total_tokens"):
                                            span.set_attribute(
                                                f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.{i}", usage.total_tokens
                                            )
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
                            if _agent_execution_time_histogram:
                                # Create shared attributes following OpenAI conventions
                                shared_attributes = {
                                    "gen_ai.system": "openai",
                                    "gen_ai.response.model": model_name,
                                    "gen_ai.request.model": model_name,  # Standard OpenTelemetry attribute
                                    "gen_ai.operation.name": "agent_run",
                                    "agent_name": starting_agent.name,
                                    "stream": "false",
                                }

                                # Add response ID if available
                                if response_id:
                                    shared_attributes["gen_ai.response.id"] = response_id

                                logger.warning(f"[DEBUG] Final metrics attributes: {shared_attributes}")

                                _agent_execution_time_histogram.record(execution_time, attributes=shared_attributes)

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

                setattr(Runner, method_name, classmethod(instrumented_method))
            else:

                @functools.wraps(original_method)
                def instrumented_method(
                    cls,
                    starting_agent,
                    input,
                    context=None,
                    max_turns=10,
                    hooks=None,
                    run_config=None,
                    _method_name=method_name,
                    _original=original_method,
                    _tracer_provider=tracer_provider,
                ):
                    start_time = time.time()

                    # Get the current tracer
                    tracer = get_tracer(__name__, __version__, _tracer_provider)

                    # Extract model information from agent and run_config
                    model_info = get_model_info(starting_agent, run_config)
                    model_name = model_info.get("model_name", "unknown")
                    logger.warning(f"[DEBUG] Extracted model name: {model_name}")

                    # Record agent run counter
                    if _agent_run_counter:
                        _agent_run_counter.add(
                            1,
                            {
                                "agent_name": starting_agent.name,
                                "method": _method_name,
                                "stream": "false",
                                "model": model_name,
                            },
                        )

                    # Create span attributes
                    attributes = {
                        "span.kind": WorkflowAttributes.WORKFLOW_STEP,
                        "agent.name": starting_agent.name,
                        WorkflowAttributes.WORKFLOW_INPUT: str(input)[:1000],
                        WorkflowAttributes.MAX_TURNS: max_turns,
                        "service.name": "agentops.agents",
                        WorkflowAttributes.WORKFLOW_TYPE: f"agents.{_method_name}",
                        SpanAttributes.LLM_REQUEST_MODEL: model_name,
                        "gen_ai.request.model": model_name,  # Standard OpenTelemetry attribute
                        "gen_ai.system": "openai",  # Standard OpenTelemetry attribute
                        "stream": "false",
                    }

                    # Add model parameters from model_info
                    for param, value in model_info.items():
                        if param != "model_name":
                            attributes[f"agent.model.{param}"] = value

                    # Create a default RunConfig if None is provided
                    if run_config is None:
                        run_config = RunConfig(workflow_name=f"Agent {starting_agent.name}")

                    if hasattr(run_config, "workflow_name"):
                        attributes[WorkflowAttributes.WORKFLOW_NAME] = run_config.workflow_name

                    # Create default hooks if None is provided
                    if hooks is None:
                        hooks = RunHooks()

                    # Start a span for the run
                    with tracer.start_as_current_span(
                        name=f"agents.{_method_name}.{starting_agent.name}", kind=SpanKind.CLIENT, attributes=attributes
                    ) as span:
                        # Add agent attributes
                        if hasattr(starting_agent, "instructions"):
                            # Determine instruction type
                            instruction_type = "unknown"
                            if isinstance(starting_agent.instructions, str):
                                instruction_type = "string"
                                span.set_attribute("agent.instructions", starting_agent.instructions[:1000])
                            elif callable(starting_agent.instructions):
                                instruction_type = "function"
                                # Store the function name or representation
                                func_name = getattr(
                                    starting_agent.instructions, "__name__", str(starting_agent.instructions)
                                )
                                span.set_attribute("agent.instruction_function", func_name)
                            else:
                                span.set_attribute("agent.instructions", str(starting_agent.instructions)[:1000])

                            span.set_attribute("agent.instruction_type", instruction_type)

                        # Add agent tools if available
                        if hasattr(starting_agent, "tools") and starting_agent.tools:
                            tool_names = [tool.name for tool in starting_agent.tools if hasattr(tool, "name")]
                            if tool_names:
                                span.set_attribute(AgentAttributes.AGENT_TOOLS, str(tool_names))

                        # Add agent model settings if available
                        if hasattr(starting_agent, "model_settings") and starting_agent.model_settings:
                            # Add model settings directly
                            if (
                                hasattr(starting_agent.model_settings, "temperature")
                                and starting_agent.model_settings.temperature is not None
                            ):
                                span.set_attribute(
                                    SpanAttributes.LLM_REQUEST_TEMPERATURE, starting_agent.model_settings.temperature
                                )

                            if (
                                hasattr(starting_agent.model_settings, "top_p")
                                and starting_agent.model_settings.top_p is not None
                            ):
                                span.set_attribute(
                                    SpanAttributes.LLM_REQUEST_TOP_P, starting_agent.model_settings.top_p
                                )

                            if (
                                hasattr(starting_agent.model_settings, "frequency_penalty")
                                and starting_agent.model_settings.frequency_penalty is not None
                            ):
                                span.set_attribute(
                                    SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY,
                                    starting_agent.model_settings.frequency_penalty,
                                )

                            if (
                                hasattr(starting_agent.model_settings, "presence_penalty")
                                and starting_agent.model_settings.presence_penalty is not None
                            ):
                                span.set_attribute(
                                    SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY,
                                    starting_agent.model_settings.presence_penalty,
                                )

                        try:
                            # Execute the original method with keyword arguments
                            result = _original(
                                starting_agent,
                                input,
                                context=context,
                                max_turns=max_turns,
                                hooks=hooks,
                                run_config=run_config,
                            )

                            # Add result attributes to the span
                            if hasattr(result, "final_output"):
                                span.set_attribute(WorkflowAttributes.FINAL_OUTPUT, str(result.final_output)[:1000])

                            # Extract model and response information
                            response_id = None

                            # Process raw responses
                            if hasattr(result, "raw_responses") and result.raw_responses:
                                logger.warning(f"[DEBUG] Found raw_responses: {len(result.raw_responses)}")
                                total_input_tokens = 0
                                total_output_tokens = 0
                                total_tokens = 0

                                for i, response in enumerate(result.raw_responses):
                                    logger.warning(f"[DEBUG] Processing raw_response {i}: {type(response).__name__}")

                                    # Try to extract model directly
                                    if hasattr(response, "model"):
                                        model_name = response.model
                                        logger.warning(f"[DEBUG] Found model in raw_response: {model_name}")
                                        span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, model_name)

                                    # Extract response ID if available
                                    if hasattr(response, "referenceable_id") and response.referenceable_id:
                                        response_id = response.referenceable_id
                                        logger.warning(f"[DEBUG] Found response_id: {response_id}")
                                        span.set_attribute(f"gen_ai.response.id.{i}", response_id)

                                    # Extract usage information
                                    if hasattr(response, "usage"):
                                        usage = response.usage
                                        logger.warning(f"[DEBUG] Found usage: {usage}")

                                        # Add token usage
                                        if hasattr(usage, "prompt_tokens") or hasattr(usage, "input_tokens"):
                                            input_tokens = getattr(
                                                usage, "prompt_tokens", getattr(usage, "input_tokens", 0)
                                            )
                                            span.set_attribute(
                                                f"{SpanAttributes.LLM_USAGE_PROMPT_TOKENS}.{i}", input_tokens
                                            )
                                            total_input_tokens += input_tokens

                                            if _agent_token_usage_histogram:
                                                _agent_token_usage_histogram.record(
                                                    input_tokens,
                                                    {
                                                        "token_type": "input",
                                                        "model": model_name,
                                                        "gen_ai.request.model": model_name,
                                                        "gen_ai.system": "openai",
                                                    },
                                                )

                                        if hasattr(usage, "completion_tokens") or hasattr(usage, "output_tokens"):
                                            output_tokens = getattr(
                                                usage, "completion_tokens", getattr(usage, "output_tokens", 0)
                                            )
                                            span.set_attribute(
                                                f"{SpanAttributes.LLM_USAGE_COMPLETION_TOKENS}.{i}", output_tokens
                                            )
                                            total_output_tokens += output_tokens

                                            if _agent_token_usage_histogram:
                                                _agent_token_usage_histogram.record(
                                                    output_tokens,
                                                    {
                                                        "token_type": "output",
                                                        "model": model_name,
                                                        "gen_ai.request.model": model_name,
                                                        "gen_ai.system": "openai",
                                                    },
                                                )

                                        if hasattr(usage, "total_tokens"):
                                            span.set_attribute(
                                                f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.{i}", usage.total_tokens
                                            )
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
                            if _agent_execution_time_histogram:
                                # Create shared attributes following OpenAI conventions
                                shared_attributes = {
                                    "gen_ai.system": "openai",
                                    "gen_ai.response.model": model_name,
                                    "gen_ai.request.model": model_name,  # Standard OpenTelemetry attribute
                                    "gen_ai.operation.name": "agent_run",
                                    "agent_name": starting_agent.name,
                                    "stream": "false",
                                }

                                # Add response ID if available
                                if response_id:
                                    shared_attributes["gen_ai.response.id"] = response_id

                                logger.warning(f"[DEBUG] Final metrics attributes: {shared_attributes}")

                                _agent_execution_time_histogram.record(execution_time, attributes=shared_attributes)

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

                setattr(Runner, method_name, classmethod(instrumented_method))

    def _uninstrument(self, **kwargs):
        """Uninstrument the Agents SDK."""
        # Restore original methods
        try:
            from agents.run import Runner

            # Check if we have the original methods stored
            if hasattr(Runner, "_original_run"):
                Runner.run = Runner._original_run
                delattr(Runner, "_original_run")

            if hasattr(Runner, "_original_run_sync"):
                Runner.run_sync = Runner._original_run_sync
                delattr(Runner, "_original_run_sync")

        except Exception as e:
            logger.warning(f"Failed to restore original Runner methods: {e}")
            pass

        # Clear active streaming operations
        global _active_streaming_operations
        _active_streaming_operations.clear()


# Helper function to manually flush spans for active streaming operations
def flush_active_streaming_operations(tracer_provider=None):
    """
    Manually flush spans for active streaming operations.

    This function can be called to force flush spans for active streaming operations
    before shutting down the trace provider.
    """
    global _active_streaming_operations

    if not _active_streaming_operations:
        return

    # Get the current trace context
    current_span = get_current_span()
    current_trace_id = None
    current_span_id = None

    # Extract trace ID and span ID from current span if available
    if hasattr(current_span, "get_span_context"):
        span_context = current_span.get_span_context()
        if hasattr(span_context, "trace_id"):
            current_trace_id = span_context.trace_id
        if hasattr(span_context, "span_id"):
            current_span_id = span_context.span_id

    # Create a new span for each active streaming operation
    if tracer_provider:
        tracer = get_tracer(__name__, __version__, tracer_provider)

        for stream_id in list(_active_streaming_operations):
            try:
                # Create attributes for the flush span
                flush_attributes = {
                    "stream_id": str(stream_id),
                    "service.name": "agentops.agents",
                    "flush_type": "manual",
                    InstrumentationAttributes.NAME: "agentops.agents",
                    InstrumentationAttributes.VERSION: __version__,
                }

                # Add trace ID if available to ensure same trace
                if current_trace_id:
                    flush_attributes[CoreAttributes.TRACE_ID] = current_trace_id

                # Add parent span ID if available
                if current_span_id:
                    flush_attributes[CoreAttributes.PARENT_ID] = current_span_id

                # Create a new span for this streaming operation
                with tracer.start_as_current_span(
                    name=f"agents.streaming.flush.{stream_id}", kind=SpanKind.INTERNAL, attributes=flush_attributes
                ) as span:
                    # Add a marker to indicate this is a flush span
                    span.set_attribute("flush_marker", "true")

                    # Force flush this span
                    if hasattr(tracer_provider, "force_flush"):
                        try:
                            tracer_provider.force_flush()
                        except Exception as e:
                            logger.warning(f"[DEBUG] Error flushing span for streaming operation {stream_id}: {e}")
            except Exception as e:
                logger.warning(f"[DEBUG] Error creating flush span for streaming operation {stream_id}: {e}")

    # Wait a short time to allow the flush to complete
    time.sleep(0.5)
