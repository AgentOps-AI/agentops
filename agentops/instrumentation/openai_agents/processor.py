from typing import Any, Dict
import time

# Import directly from the source modules instead of re-exporting
from opentelemetry.trace import get_tracer
from opentelemetry.metrics import get_meter
from agentops.semconv.meters import Meters
from agentops.semconv import SpanAttributes
from agentops.helpers.serialization import model_to_dict
from agentops.logging import logger

from agentops.instrumentation.openai_agents import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.openai_agents.exporter import OpenAIAgentsExporter

class OpenAIAgentsProcessor:
    """Processor for OpenAI Agents SDK traces.
    
    This processor implements the TracingProcessor interface from the Agents SDK
    and converts trace events to OpenTelemetry spans and metrics.
    """
    
    def __init__(self, tracer_provider=None, meter_provider=None):
        self.tracer_provider = tracer_provider
        self.meter_provider = meter_provider
        
        # Create both a tracer for direct span creation and an exporter for translation
        self.tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider) if tracer_provider else None
        self.exporter = OpenAIAgentsExporter(tracer_provider)
        
        # Initialize metrics
        self._agent_run_counter = None
        self._agent_execution_time_histogram = None
        self._agent_token_usage_histogram = None
        
        # Track active traces for timing
        self._active_traces = {}  # trace_id -> (start_time, metadata)
        
        if meter_provider:
            self._initialize_metrics(meter_provider)
    
    def _initialize_metrics(self, meter_provider):
        """Initialize OpenTelemetry metrics."""
        meter = get_meter(LIBRARY_NAME, LIBRARY_VERSION, meter_provider)
        
        self._agent_run_counter = meter.create_counter(
            name="agents.runs", 
            unit="run", 
            description="Counts agent runs"
        )
        
        self._agent_execution_time_histogram = meter.create_histogram(
            name=Meters.LLM_OPERATION_DURATION, 
            unit="s", 
            description="GenAI operation duration"
        )
        
        self._agent_token_usage_histogram = meter.create_histogram(
            name=Meters.LLM_TOKEN_USAGE, 
            unit="token", 
            description="Measures token usage in agent runs"
        )
    
    def on_trace_start(self, trace: Any) -> None:
        """Called when a trace starts in the Agents SDK."""
        if not hasattr(trace, 'trace_id'):
            logger.debug("Trace does not have trace_id attribute, skipping")
            return
            
        # Record trace start time and metadata
        workflow_name = getattr(trace, 'name', 'unknown')
        logger.debug(f"Starting trace: {workflow_name} (ID: {trace.trace_id})")
        
        self._active_traces[trace.trace_id] = {
            'start_time': time.time(),
            'workflow_name': workflow_name,
            'agent_name': workflow_name,
            'model_name': 'unknown',
            'is_streaming': 'false'
        }
        
        # Use the exporter to create a span from the trace
        self.exporter.export_trace(trace)

    def on_trace_end(self, trace: Any) -> None:
        """Called when a trace ends in the Agents SDK."""
        if not hasattr(trace, 'trace_id'):
            logger.debug("Trace does not have trace_id attribute, skipping")
            return
            
        if trace.trace_id not in self._active_traces:
            logger.debug(f"Trace ID {trace.trace_id} not found in active traces, may be missing start event")
            return
        
        # Get trace metadata and calculate duration
        trace_data = self._active_traces.pop(trace.trace_id)
        execution_time = time.time() - trace_data['start_time']
        logger.debug(f"Ending trace: {trace_data['workflow_name']} (ID: {trace.trace_id}), duration: {execution_time:.2f}s")
        
        # Record execution time metric
        if self._agent_execution_time_histogram:
            self._agent_execution_time_histogram.record(
                execution_time, 
                attributes={
                    SpanAttributes.LLM_SYSTEM: "openai",
                    "gen_ai.response.model": trace_data['model_name'],
                    SpanAttributes.LLM_REQUEST_MODEL: trace_data['model_name'],
                    "gen_ai.operation.name": "agent_run",
                    "agent_name": trace_data['agent_name'],
                    "stream": trace_data['is_streaming'],
                }
            )
        
        # Use the exporter to create a span from the trace
        self.exporter.export_trace(trace)

    def on_span_start(self, span: Any) -> None:
        """Called when a span starts in the Agents SDK."""
        if not hasattr(span, 'span_data'):
            return
        
        span_data = span.span_data
        span_type = span_data.__class__.__name__
        span_id = getattr(span, 'span_id', 'unknown')
        logger.debug(f"Processing span start: Type={span_type}, ID={span_id}")
        
        # Extract agent name for metrics
        agent_name = self._extract_agent_name(span_data)
        
        # Extract trace metadata if available
        trace_id = getattr(span, 'trace_id', None)
        trace_data = self._active_traces.get(trace_id, {}) if trace_id else {}
        
        # Update trace data with agent information if available
        if trace_id in self._active_traces and agent_name != 'unknown':
            self._active_traces[trace_id]['agent_name'] = agent_name
        
        # Record agent run metrics for AgentSpanData
        if span_type == "AgentSpanData" and self._agent_run_counter:
            model_name = self._extract_model_name(span_data)
            is_streaming = trace_data.get('is_streaming', 'false')
            
            # Update trace data with model information
            if trace_id in self._active_traces and model_name != 'unknown':
                self._active_traces[trace_id]['model_name'] = model_name
            
            # Record agent run
            self._agent_run_counter.add(
                1,
                {
                    "agent_name": agent_name,
                    "method": "run",  # Generic since we don't know exact method
                    "stream": is_streaming,
                    "model": model_name,
                }
            )
            
        # Use the exporter to create spans from the Agents SDK span
        self.exporter.export_span(span)

    def on_span_end(self, span: Any) -> None:
        """Called when a span ends in the Agents SDK."""
        if not hasattr(span, 'span_data'):
            return
        
        span_data = span.span_data
        span_type = span_data.__class__.__name__
        span_id = getattr(span, 'span_id', 'unknown')
        logger.debug(f"Processing span end: Type={span_type}, ID={span_id}")
        
        # Process generation spans for token usage metrics
        if span_type == "GenerationSpanData" and self._agent_token_usage_histogram:
            model_name = self._extract_model_name(span_data)
            
            # Extract usage data
            usage = getattr(span_data, 'usage', {})
            if not usage:
                # Try to extract from output
                output = getattr(span_data, 'output', None)
                if output:
                    output_dict = model_to_dict(output)
                    if isinstance(output_dict, dict):
                        usage = output_dict.get('usage', {})
            
            # Record token usage metrics
            if usage:
                self._record_token_usage(usage, model_name)
                
                # Update trace with model information if available
                trace_id = getattr(span, 'trace_id', None)
                if trace_id in self._active_traces and model_name != 'unknown':
                    self._active_traces[trace_id]['model_name'] = model_name
        
        # Use the exporter to create spans from the Agents SDK span
        self.exporter.export_span(span)

    def shutdown(self) -> None:
        """Called when the application stops."""
        self._active_traces.clear()

    def force_flush(self) -> None:
        """Forces an immediate flush of all queued spans/traces."""
        pass
    
    def _extract_agent_name(self, span_data: Any) -> str:
        """Extract agent name from span data."""
        if hasattr(span_data, 'name'):
            return span_data.name
        
        # Handle different span types
        if hasattr(span_data, 'from_agent') and span_data.from_agent:
            return span_data.from_agent
            
        return "unknown"
    
    def _extract_model_name(self, span_data: Any) -> str:
        """Extract model name from span data."""
        if hasattr(span_data, 'model') and span_data.model:
            return span_data.model
            
        # For generation spans with model_config
        if hasattr(span_data, 'model_config') and span_data.model_config:
            model_config = span_data.model_config
            if isinstance(model_config, dict) and 'model' in model_config:
                return model_config['model']
            if hasattr(model_config, 'model') and model_config.model:
                return model_config.model
                
        # For spans with output containing model info
        if hasattr(span_data, 'output') and span_data.output:
            output = span_data.output
            if hasattr(output, 'model') and output.model:
                return output.model
            
            # Try to extract from dict representation
            output_dict = model_to_dict(output)
            if isinstance(output_dict, dict) and 'model' in output_dict:
                return output_dict['model']
        
        # Default model
        try:
            from agents.models.openai_provider import DEFAULT_MODEL
            return DEFAULT_MODEL
        except ImportError:
            return "unknown"
    
    def _record_token_usage(self, usage: Dict[str, Any], model_name: str) -> None:
        """Record token usage metrics from usage data."""
        # Record input tokens
        input_tokens = usage.get('prompt_tokens', usage.get('input_tokens', 0))
        if input_tokens:
            self._agent_token_usage_histogram.record(
                input_tokens,
                {
                    "token_type": "input",
                    "model": model_name,
                    SpanAttributes.LLM_REQUEST_MODEL: model_name,
                    SpanAttributes.LLM_SYSTEM: "openai",
                },
            )
        
        # Record output tokens
        output_tokens = usage.get('completion_tokens', usage.get('output_tokens', 0))
        if output_tokens:
            self._agent_token_usage_histogram.record(
                output_tokens,
                {
                    "token_type": "output",
                    "model": model_name,
                    SpanAttributes.LLM_REQUEST_MODEL: model_name,
                    SpanAttributes.LLM_SYSTEM: "openai",
                },
            )
        
        # Record reasoning tokens if available
        output_tokens_details = usage.get('output_tokens_details', {})
        if isinstance(output_tokens_details, dict):
            reasoning_tokens = output_tokens_details.get('reasoning_tokens', 0)
            if reasoning_tokens:
                self._agent_token_usage_histogram.record(
                    reasoning_tokens,
                    {
                        "token_type": "reasoning",
                        "model": model_name,
                        SpanAttributes.LLM_REQUEST_MODEL: model_name,
                        SpanAttributes.LLM_SYSTEM: "openai",
                    },
                )
    