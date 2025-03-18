from typing import Any, Dict, Optional, Union
import time
import weakref
from contextlib import contextmanager

from opentelemetry import trace, context as context_api
from agentops.helpers.serialization import model_to_dict, safe_serialize
from agentops.logging import logger

from agentops.instrumentation.openai_agents import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.openai_agents.tokens import process_token_usage
from agentops.instrumentation.openai_agents.metrics import record_token_usage


def get_otel_trace_id() -> Union[str, None]:
    """
    Get the current OpenTelemetry trace ID as a hexadecimal string.
    
    This is the native trace ID that appears in the AgentOps API and is used
    for correlation between logs and the API.
    
    Returns:
        The trace ID as a 32-character hex string, or None if not available
    """
    try:
        current_span = trace.get_current_span()
        if hasattr(current_span, "get_span_context"):
            ctx = current_span.get_span_context()
            if hasattr(ctx, "trace_id") and ctx.trace_id:
                # Convert trace_id to 32-character hex string as shown in the API
                return f"{ctx.trace_id:032x}" if isinstance(ctx.trace_id, int) else str(ctx.trace_id)
    except Exception:
        pass
    return None


class OpenAIAgentsProcessor:
    """Processor for OpenAI Agents SDK traces.
    
    This processor implements the TracingProcessor interface from the Agents SDK
    and converts trace events to OpenTelemetry spans and metrics.
    
    It is responsible for:
    1. Processing raw API responses from the Agents SDK
    2. Extracting relevant data from span objects
    3. Preparing standardized data for the exporter
    4. Tracking relationships between spans and traces
    
    NOTE: The processor does NOT directly create OpenTelemetry spans.
    It delegates span creation to the OpenAIAgentsExporter.
    """
    
    def __init__(self, exporter=None, meter_provider=None):
        self.exporter = exporter
        self.meter_provider = meter_provider
        
        # Initialize metrics
        self._agent_run_counter = None
        self._agent_execution_time_histogram = None
        self._agent_token_usage_histogram = None
        
        # Track active traces
        self._active_traces = {}  # trace_id -> metadata with timing, etc.
        
        if meter_provider:
            self._initialize_metrics(meter_provider)
    
    def _initialize_metrics(self, meter_provider):
        """Initialize OpenTelemetry metrics."""
        from opentelemetry.metrics import get_meter
        from agentops.semconv.meters import Meters
        
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
    
    def on_trace_start(self, sdk_trace: Any) -> None:
        """Called when a trace starts in the Agents SDK."""
        if not hasattr(sdk_trace, 'trace_id'):
            logger.debug("[TRACE] Missing trace_id attribute, operation skipped")
            return
        
        # Record trace start time and metadata
        workflow_name = getattr(sdk_trace, 'name', 'unknown')
        trace_id = getattr(sdk_trace, 'trace_id', 'unknown')
        
        # Store basic trace information
        self._active_traces[trace_id] = {
            'start_time': time.time(),
            'workflow_name': workflow_name,
            'agent_name': workflow_name,
            'model_name': 'unknown',
            'is_streaming': 'false',
        }
        
        # Forward to exporter if available
        if self.exporter:
            # Get the OpenTelemetry root trace ID that appears in the AgentOps API
            otel_trace_id = get_otel_trace_id()
            
            # Log trace start with root trace ID if available
            if otel_trace_id:
                logger.debug(f"[TRACE] Started: {workflow_name} | TRACE ID: {otel_trace_id}")
            else:
                logger.debug(f"[TRACE] Started: {workflow_name} | No OTel trace ID available")
                
            self.exporter.export_trace(sdk_trace)

    def on_trace_end(self, sdk_trace: Any) -> None:
        """Called when a trace ends in the Agents SDK."""
        if not hasattr(sdk_trace, 'trace_id'):
            logger.debug("[TRACE] Missing trace_id attribute, operation skipped")
            return
            
        trace_id = sdk_trace.trace_id
        if trace_id not in self._active_traces:
            logger.debug(f"[TRACE] Trace ID {trace_id} not found in active traces, may be missing start event")
            return
        
        # Get trace metadata and calculate duration
        trace_data = self._active_traces[trace_id]
        start_time = trace_data.get('start_time', time.time())
        execution_time = time.time() - start_time
        workflow_name = trace_data.get('workflow_name', 'unknown')
        
        # Get the OpenTelemetry root trace ID that appears in the AgentOps API
        otel_trace_id = get_otel_trace_id()
        
        # Log trace end with root trace ID if available
        if otel_trace_id:
            logger.debug(f"[TRACE] Ended: {workflow_name} | TRACE ID: {otel_trace_id} | Duration: {execution_time:.2f}s")
        else:
            logger.debug(f"[TRACE] Ended: {workflow_name} | Duration: {execution_time:.2f}s")
        
        # Record execution time metric
        if self._agent_execution_time_histogram:
            from agentops.semconv import SpanAttributes
            
            self._agent_execution_time_histogram.record(
                execution_time, 
                attributes={
                    SpanAttributes.LLM_SYSTEM: "openai",
                    "gen_ai.response.model": trace_data.get('model_name', 'unknown'),
                    SpanAttributes.LLM_REQUEST_MODEL: trace_data.get('model_name', 'unknown'),
                    "gen_ai.operation.name": "agent_run",
                    "agent_name": trace_data.get('agent_name', 'unknown'),
                    "stream": trace_data.get('is_streaming', 'false'),
                }
            )
        
        # Forward to exporter if available
        if self.exporter:
            self.exporter.export_trace(sdk_trace)
        
        # Clean up trace resources
        self._active_traces.pop(trace_id, None)

    def on_span_start(self, span: Any) -> None:
        """Called when a span starts in the Agents SDK."""
        if not hasattr(span, 'span_data'):
            return
        
        span_data = span.span_data
        span_type = span_data.__class__.__name__
        span_id = getattr(span, 'span_id', 'unknown')
        trace_id = getattr(span, 'trace_id', None)
        parent_id = getattr(span, 'parent_id', None)
        
        logger.debug(f"[SPAN] Started: {span_type} | ID: {span_id} | Parent: {parent_id}")
        
        # Extract agent name for metrics
        agent_name = self._extract_agent_name(span_data)
        
        # Update trace data with agent information if available
        if trace_id in self._active_traces and agent_name != 'unknown':
            self._active_traces[trace_id]['agent_name'] = agent_name
        
        # Record agent run metrics for AgentSpanData
        if span_type == "AgentSpanData" and self._agent_run_counter:
            model_name = self._extract_model_name(span_data)
            is_streaming = self._active_traces.get(trace_id, {}).get('is_streaming', 'false')
            
            # Update trace data with model information
            if trace_id in self._active_traces and model_name != 'unknown':
                self._active_traces[trace_id]['model_name'] = model_name
            
            # Record agent run
            self._agent_run_counter.add(
                1,
                {
                    "agent_name": agent_name,
                    "method": "run",
                    "stream": is_streaming,
                    "model": model_name,
                }
            )
        
        # Forward to exporter if available
        if self.exporter:
            self.exporter.export_span(span)

    def on_span_end(self, span: Any) -> None:
        """Called when a span ends in the Agents SDK."""
        if not hasattr(span, 'span_data'):
            return
        
        span_data = span.span_data
        span_type = span_data.__class__.__name__
        span_id = getattr(span, 'span_id', 'unknown')
        trace_id = getattr(span, 'trace_id', None)
        
        logger.debug(f"[SPAN] Ended: {span_type} | ID: {span_id}")
        
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
                record_token_usage(self._agent_token_usage_histogram, usage, model_name)
                
                # Update trace with model information if available
                if trace_id in self._active_traces and model_name != 'unknown':
                    self._active_traces[trace_id]['model_name'] = model_name
        
        # Forward to exporter if available
        if self.exporter:
            self.exporter.export_span(span)
    
    def shutdown(self) -> None:
        """Called when the application stops."""
        # Log debug info about resources being cleaned up and clear
        logger.debug(f"[PROCESSOR] Shutting down - cleaning up {len(self._active_traces)} traces")
        self._active_traces.clear()

    def force_flush(self) -> None:
        """Forces an immediate flush of all queued spans/traces."""
        # We don't queue spans so this is a no-op
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