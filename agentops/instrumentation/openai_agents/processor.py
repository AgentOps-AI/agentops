from typing import Any, Dict
import time
import weakref
from contextlib import contextmanager

# Import directly from the source modules instead of re-exporting
from opentelemetry.trace import get_tracer, SpanKind, Status, StatusCode
from opentelemetry.metrics import get_meter
from opentelemetry import trace, context as context_api
from agentops.semconv.meters import Meters
from agentops.semconv import SpanAttributes, CoreAttributes, WorkflowAttributes, InstrumentationAttributes, MessageAttributes
from agentops.helpers.serialization import model_to_dict, safe_serialize
from agentops.logging import logger

from agentops.instrumentation.openai_agents import LIBRARY_NAME, LIBRARY_VERSION

class OpenAIAgentsProcessor:
    """Processor for OpenAI Agents SDK traces.
    
    This processor implements the TracingProcessor interface from the Agents SDK
    and converts trace events to OpenTelemetry spans and metrics.
    
    This implementation uses OpenTelemetry's context managers to properly maintain
    parent-child relationships between spans and ensures context propagation.
    """
    
    def __init__(self, tracer_provider=None, meter_provider=None):
        self.tracer_provider = tracer_provider
        self.meter_provider = meter_provider
        
        # Create tracer for span creation
        self.tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider) if tracer_provider else None
        
        # Initialize metrics
        self._agent_run_counter = None
        self._agent_execution_time_histogram = None
        self._agent_token_usage_histogram = None
        
        # Track active traces and spans
        self._active_traces = {}  # trace_id -> metadata with timing, span, etc.
        self._active_spans = weakref.WeakValueDictionary()  # span_id -> OTEL span object
        
        # Store span contexts for proper parent-child relationships
        self._span_contexts = {}  # span_id -> OpenTelemetry SpanContext object
        self._trace_root_contexts = {}  # trace_id -> OpenTelemetry Context object for the root span
        
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
    
    def _get_parent_context(self, parent_id, trace_id):
        """Get the parent context for a span based on parent ID or trace ID.
        
        Args:
            parent_id: The parent span ID if available
            trace_id: The trace ID this span belongs to
            
        Returns:
            An OpenTelemetry Context object with the parent span, or None
        """
        # First try to find the direct parent context
        if parent_id and parent_id in self._span_contexts:
            parent_context = self._span_contexts[parent_id]
            logger.debug(f"Found parent context for {parent_id}")
            return parent_context
            
        # If no direct parent found but we have a trace, use the trace's root context
        if trace_id and trace_id in self._trace_root_contexts:
            root_context = self._trace_root_contexts[trace_id]
            logger.debug(f"Using trace root context for {trace_id}")
            return root_context
            
        # Fall back to current context
        logger.debug(f"No specific parent context found, using current context")
        return context_api.get_current()
        
    @contextmanager
    def create_span(self, name, kind, attributes=None, parent=None, end_on_exit=True):
        """Context manager for creating spans with proper parent-child relationship.
        
        Args:
            name: Name for the span
            kind: SpanKind for the span
            attributes: Optional dict of attributes to set on the span
            parent: Optional parent span ID to link this span to
            end_on_exit: Whether to end the span when exiting the context manager
            
        Yields:
            The created span object
        """
        attributes = attributes or {}
        
        # Add trace correlation attributes for easier querying
        if "agentops.trace_hash" not in attributes and "agentops.original_trace_id" in attributes:
            # Create a consistent hash for all spans with the same original trace ID
            trace_hash = hash(attributes["agentops.original_trace_id"]) % 10000
            attributes["agentops.trace_hash"] = str(trace_hash)
        
        # Determine the parent context for this span
        trace_id = attributes.get("agentops.original_trace_id")
        parent_context = self._get_parent_context(parent, trace_id)
        
        # Create the span with explicit parent context
        with self.tracer.start_as_current_span(
            name=name,
            kind=kind,
            attributes=attributes,
            context=parent_context
        ) as span:
            # Store span context for future parent references
            span_id = attributes.get("agentops.original_span_id")
            if span_id:
                # Store the span context for future child spans
                self._span_contexts[span_id] = trace.set_span_in_context(span)
                logger.debug(f"Stored context for span {span_id}")
                
                # If this is a root span, also store as trace root
                if attributes.get("agentops.is_root_span") == "true" and trace_id:
                    self._trace_root_contexts[trace_id] = trace.set_span_in_context(span)
                    logger.debug(f"Stored root context for trace {trace_id}")
            
            # Store the span object itself
            span_key = attributes.get("agentops.original_span_id", name)
            self._active_spans[span_key] = span
            
            # Debug output to help with context tracking
            if hasattr(span, "context") and hasattr(span.context, "trace_id"):
                otel_trace_id = f"{span.context.trace_id:x}"
                otel_span_id = f"{span.context.span_id:x}" if hasattr(span.context, "span_id") else "unknown"
                
                if parent:
                    logger.debug(f"Created child span {otel_span_id} with parent={parent} in trace {otel_trace_id}")
                else:
                    logger.debug(f"Created span {otel_span_id} in trace {otel_trace_id}")
            
            # Yield the span for use within the context manager
            yield span
    
    def on_trace_start(self, sdk_trace: Any) -> None:
        """Called when a trace starts in the Agents SDK."""
        if not hasattr(sdk_trace, 'trace_id'):
            logger.debug("Trace does not have trace_id attribute, skipping")
            return
        
        # Record trace start time and metadata
        workflow_name = getattr(sdk_trace, 'name', 'unknown')
        trace_id = getattr(sdk_trace, 'trace_id', 'unknown')
        logger.debug(f"Starting trace: {workflow_name} (ID: {trace_id})")
        
        # Store basic trace information
        self._active_traces[trace_id] = {
            'start_time': time.time(),
            'workflow_name': workflow_name,
            'agent_name': workflow_name,
            'model_name': 'unknown',
            'is_streaming': 'false',
        }
        
        # Create a proper span for the trace using context manager
        # This will be the root span for this trace
        with self.create_span(
            name=f"agents.trace.{workflow_name}",
            kind=SpanKind.INTERNAL,
            attributes={
                WorkflowAttributes.WORKFLOW_NAME: workflow_name,
                CoreAttributes.TRACE_ID: trace_id,
                InstrumentationAttributes.NAME: LIBRARY_NAME,
                InstrumentationAttributes.VERSION: LIBRARY_VERSION,
                WorkflowAttributes.WORKFLOW_STEP_TYPE: "trace",
                "agentops.original_trace_id": trace_id,
                "agentops.is_root_span": "true",
            }
        ) as span:
            # Store the trace span for later reference
            self._active_traces[trace_id]['span'] = span
            self._active_spans[trace_id] = span
            
            # Store the span context specifically for this trace root
            # This ensures all spans from this trace use the same trace ID
            if hasattr(span, "context"):
                # Use OpenTelemetry's trace module (imported at top) to store the span in context
                otel_context = trace.set_span_in_context(span)
                self._trace_root_contexts[trace_id] = otel_context
                
                # For debugging, extract trace ID
                if hasattr(span.context, "trace_id"):
                    otel_trace_id = f"{span.context.trace_id:x}"
                    self._active_traces[trace_id]['otel_trace_id'] = otel_trace_id
                    logger.debug(f"Created root trace span {trace_id} with OTel trace ID {otel_trace_id}")
                    logger.debug(f"Stored root context for future spans in trace {trace_id}")
            
            # Add any additional trace attributes
            if hasattr(sdk_trace, "group_id") and sdk_trace.group_id:
                span.set_attribute(CoreAttributes.GROUP_ID, sdk_trace.group_id)
                
            if hasattr(sdk_trace, "metadata") and sdk_trace.metadata:
                for key, value in sdk_trace.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        span.set_attribute(f"trace.metadata.{key}", value)

    def on_trace_end(self, sdk_trace: Any) -> None:
        """Called when a trace ends in the Agents SDK."""
        if not hasattr(sdk_trace, 'trace_id'):
            logger.debug("Trace does not have trace_id attribute, skipping")
            return
            
        trace_id = sdk_trace.trace_id
        if trace_id not in self._active_traces:
            logger.debug(f"Trace ID {trace_id} not found in active traces, may be missing start event")
            return
        
        # Get trace metadata and calculate duration
        trace_data = self._active_traces[trace_id]
        start_time = trace_data.get('start_time', time.time())
        execution_time = time.time() - start_time
        logger.debug(f"Ending trace: {trace_data.get('workflow_name', 'unknown')} (ID: {trace_id}), duration: {execution_time:.2f}s")
        
        # Record execution time metric
        if self._agent_execution_time_histogram:
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
        
        # Get the root trace context to ensure proper trace linking
        root_context = None
        if trace_id in self._trace_root_contexts:
            root_context = self._trace_root_contexts[trace_id]
            logger.debug(f"Using stored root context for trace end span in trace {trace_id}")
        
        # Create a span for trace end using the trace's root context
        # This ensures the end span is part of the same trace as the start span
        with self.create_span(
            name=f"agents.trace.{trace_data.get('workflow_name', 'unknown')}",
            kind=SpanKind.INTERNAL,
            attributes={
                WorkflowAttributes.WORKFLOW_NAME: trace_data.get('workflow_name', 'unknown'),
                CoreAttributes.TRACE_ID: trace_id,
                InstrumentationAttributes.NAME: LIBRARY_NAME,
                InstrumentationAttributes.VERSION: LIBRARY_VERSION,
                WorkflowAttributes.WORKFLOW_STEP_TYPE: "trace_end",
                "agentops.original_trace_id": trace_id,
                "execution_time_seconds": execution_time,
            },
            parent=trace_id  # Pass trace_id as parent to link to root span
        ) as span:
            # Verify the trace ID matches the root trace to confirm proper context propagation
            if hasattr(span, "context") and hasattr(span.context, "trace_id"):
                otel_trace_id = f"{span.context.trace_id:x}"
                if 'otel_trace_id' in trace_data:
                    root_trace_id = trace_data['otel_trace_id']
                    if otel_trace_id == root_trace_id:
                        logger.debug(f"Trace end span successfully linked to trace {trace_id} with OTel trace ID {otel_trace_id}")
                    else:
                        logger.warning(f"Trace end span has different OTel trace ID ({otel_trace_id}) than root trace ({root_trace_id})")
        
        # Clean up trace resources
        self._active_traces.pop(trace_id, None)
        self._trace_root_contexts.pop(trace_id, None)
        
        logger.debug(f"Cleaned up trace resources for trace {trace_id}")

    def on_span_start(self, span: Any) -> None:
        """Called when a span starts in the Agents SDK."""
        if not hasattr(span, 'span_data'):
            return
        
        span_data = span.span_data
        span_type = span_data.__class__.__name__
        span_id = getattr(span, 'span_id', 'unknown')
        trace_id = getattr(span, 'trace_id', None)
        parent_id = getattr(span, 'parent_id', None)
        
        logger.debug(f"Processing span start: Type={span_type}, ID={span_id}, Parent={parent_id}")
        
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
        
        # Build span attributes based on span type
        attributes = self._build_span_attributes(span, span_data, span_type)
        
        # Add trace/parent relationship attributes
        attributes.update({
            "agentops.original_trace_id": trace_id,
            "agentops.original_span_id": span_id,
        })
        
        # Set parent relationship attribute and root span flag
        if parent_id:
            attributes["agentops.parent_span_id"] = parent_id
        else:
            attributes["agentops.is_root_span"] = "true"
        
        # Generate span name based on type
        span_name = f"agents.{span_type.replace('SpanData', '').lower()}"
        
        # Determine span kind based on span type
        span_kind = self._get_span_kind(span_type)
        
        # Create the span with parent context and store its context for future spans
        # Our create_span context manager will:
        # 1. Find the appropriate parent context using trace_id and parent_id
        # 2. Create the span with that context to maintain trace continuity
        # 3. Store the span context for future child spans
        with self.create_span(
            name=span_name,
            kind=span_kind,
            attributes=attributes,
            parent=parent_id  # Pass parent_id to create proper parent-child relationship
        ) as otel_span:
            # Store the span for future reference
            self._active_spans[span_id] = otel_span
            
            # For debugging, log span creation with detailed context information
            if hasattr(otel_span, "context") and hasattr(otel_span.context, "trace_id"):
                otel_trace_id = f"{otel_span.context.trace_id:x}"
                otel_span_id = f"{otel_span.context.span_id:x}" if hasattr(otel_span.context, "span_id") else "unknown"
                
                parent_context = ""
                if parent_id and parent_id in self._span_contexts:
                    parent_span = trace.get_current_span(self._span_contexts[parent_id])
                    if hasattr(parent_span, "context") and hasattr(parent_span.context, "span_id"):
                        parent_span_id = f"{parent_span.context.span_id:x}"
                        parent_context = f", parent span={parent_span_id}"
                
                logger.debug(f"Created span {otel_span_id} for SDK span {span_id} in trace {otel_trace_id}{parent_context}")
                
                # Check if this span has the same trace ID as its parent or trace root
                if trace_id in self._active_traces and 'otel_trace_id' in self._active_traces[trace_id]:
                    root_trace_id = self._active_traces[trace_id]['otel_trace_id']
                    if otel_trace_id == root_trace_id:
                        logger.debug(f"Span {span_id} successfully linked to trace {trace_id} with OTel trace ID {otel_trace_id}")
                    else:
                        logger.warning(f"Span {span_id} has different OTel trace ID ({otel_trace_id}) than root trace ({root_trace_id})")

    def on_span_end(self, span: Any) -> None:
        """Called when a span ends in the Agents SDK."""
        if not hasattr(span, 'span_data'):
            return
        
        span_data = span.span_data
        span_type = span_data.__class__.__name__
        span_id = getattr(span, 'span_id', 'unknown')
        trace_id = getattr(span, 'trace_id', None)
        
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
                if trace_id in self._active_traces and model_name != 'unknown':
                    self._active_traces[trace_id]['model_name'] = model_name
        
        # If we have the span in our active spans, we'll close it automatically
        # No need to do anything here; the context manager handles ending the span
        
        # Clean up our reference if it exists
        self._active_spans.pop(span_id, None)
    
    def _get_span_kind(self, span_type):
        """Determine the appropriate span kind based on span type."""
        if span_type == "AgentSpanData":
            return SpanKind.CONSUMER
        elif span_type in ["FunctionSpanData", "GenerationSpanData", "ResponseSpanData"]:
            return SpanKind.CLIENT
        else:
            return SpanKind.INTERNAL
    
    def _build_span_attributes(self, span, span_data, span_type):
        """Build span attributes based on span type."""
        attributes = {
            InstrumentationAttributes.NAME: LIBRARY_NAME,
            InstrumentationAttributes.VERSION: LIBRARY_VERSION,
        }
        
        # Handle common attributes
        if hasattr(span_data, 'name'):
            attributes["agent.name"] = span_data.name
        
        # Process span data based on type
        if span_type == "AgentSpanData":
            if hasattr(span_data, 'input'):
                attributes[WorkflowAttributes.WORKFLOW_INPUT] = safe_serialize(span_data.input)
                
            if hasattr(span_data, 'output'):
                attributes[WorkflowAttributes.FINAL_OUTPUT] = safe_serialize(span_data.output)
                
            if hasattr(span_data, 'tools') and span_data.tools:
                attributes["agent.tools"] = ",".join(span_data.tools)
                
        elif span_type == "FunctionSpanData":
            if hasattr(span_data, 'input'):
                attributes[SpanAttributes.LLM_PROMPTS] = safe_serialize(span_data.input)
                
            if hasattr(span_data, 'output'):
                # Using MessageAttributes for structured completion
                attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = safe_serialize(span_data.output)
                attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] = "function"
                
            if hasattr(span_data, 'from_agent'):
                attributes["agent.from"] = span_data.from_agent
                
        elif span_type == "GenerationSpanData":
            if hasattr(span_data, 'model'):
                attributes[SpanAttributes.LLM_REQUEST_MODEL] = span_data.model
                attributes[SpanAttributes.LLM_SYSTEM] = "openai"
                
            if hasattr(span_data, 'input'):
                attributes[SpanAttributes.LLM_PROMPTS] = safe_serialize(span_data.input)
                
            if hasattr(span_data, 'output'):
                # Using MessageAttributes for structured completion
                attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = safe_serialize(span_data.output)
                attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] = "assistant"
                
            # Process usage data
            if hasattr(span_data, 'usage'):
                usage = span_data.usage
                if hasattr(usage, 'prompt_tokens') or hasattr(usage, 'input_tokens'):
                    prompt_tokens = getattr(usage, 'prompt_tokens', getattr(usage, 'input_tokens', 0))
                    attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = prompt_tokens
                    
                if hasattr(usage, 'completion_tokens') or hasattr(usage, 'output_tokens'):
                    completion_tokens = getattr(usage, 'completion_tokens', getattr(usage, 'output_tokens', 0))
                    attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = completion_tokens
                    
                if hasattr(usage, 'total_tokens'):
                    attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage.total_tokens
                
        elif span_type == "HandoffSpanData":
            if hasattr(span_data, 'from_agent'):
                attributes["agent.from"] = span_data.from_agent
                
            if hasattr(span_data, 'to_agent'):
                attributes["agent.to"] = span_data.to_agent
                
        elif span_type == "ResponseSpanData":
            if hasattr(span_data, 'input'):
                attributes[SpanAttributes.LLM_PROMPTS] = safe_serialize(span_data.input)
                
            if hasattr(span_data, 'response'):
                # Using MessageAttributes for structured completion
                attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = safe_serialize(span_data.response)
                attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] = "assistant"
        
        return attributes

    def shutdown(self) -> None:
        """Called when the application stops."""
        # Log debug info about resources being cleaned up
        logger.debug(f"Shutting down OpenAIAgentsProcessor - cleaning up {len(self._active_traces)} traces, " 
                    f"{len(self._span_contexts)} span contexts, and {len(self._trace_root_contexts)} trace root contexts")
        
        # Clean up all resources
        self._active_traces.clear()
        self._active_spans.clear()
        self._span_contexts.clear()
        self._trace_root_contexts.clear()
        logger.debug("OpenAIAgentsProcessor resources successfully cleaned up")

    def force_flush(self) -> None:
        """Forces an immediate flush of all queued spans/traces."""
        # We don't queue spans, but we could log any pending spans if needed
        logger.debug("Force flush called on OpenAIAgentsProcessor")
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
    