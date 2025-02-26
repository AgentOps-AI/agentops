"""Span processor for creating metrics from spans.

This module provides a custom span processor that intercepts spans from the TracerProvider,
determines their kinds based on span attributes, and increments the appropriate counters.
"""

from typing import Dict, Callable, Optional, Any
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult, BatchSpanProcessor
from opentelemetry.semconv_ai import SpanAttributes, LLMRequestTypeValues
from opentelemetry.metrics import get_meter
from opentelemetry import metrics

class MetricsSpanProcessor(BatchSpanProcessor):
    """A span processor that creates metrics from spans.
    
    This processor intercepts spans from the TracerProvider, determines their kinds
    based on span attributes, and increments the appropriate counters.
    """
    
    def __init__(self, exporter: SpanExporter, session_id: str, max_queue_size: int = 2048, 
                schedule_delay_millis: float = 5000, max_export_batch_size: int = 512,
                export_timeout_millis: float = 30000):
        """Initialize the metrics span processor.
        
        Args:
            exporter: The span exporter to use.
            session_id: The ID of the session.
            max_queue_size: The maximum queue size.
            schedule_delay_millis: The schedule delay in milliseconds.
            max_export_batch_size: The maximum export batch size.
            export_timeout_millis: The export timeout in milliseconds.
        """
        super().__init__(
            exporter,
            max_queue_size=max_queue_size,
            schedule_delay_millis=schedule_delay_millis,
            max_export_batch_size=max_export_batch_size,
            export_timeout_millis=export_timeout_millis,
        )
        self.session_id = session_id
        
        # Initialize meter provider if not already done
        if not metrics.get_meter_provider():
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
            
            exporter = ConsoleMetricExporter()
            reader = PeriodicExportingMetricReader(exporter)
            provider = MeterProvider(metric_readers=[reader])
            metrics.set_meter_provider(provider)
        
        # Create meter for session events
        self.meter = get_meter("agentops.session")
        
        # Create counters for different event types
        self.llm_counter = self.meter.create_counter(
            name="agentops.session.llm.calls",
            unit="call",
            description="Number of LLM API calls made during session"
        )
        
        self.tool_counter = self.meter.create_counter(
            name="agentops.session.tool.calls",
            unit="call",
            description="Number of tool calls made during session"
        )
        
        self.action_counter = self.meter.create_counter(
            name="agentops.session.actions",
            unit="action",
            description="Number of actions performed during session"
        )
        
        self.error_counter = self.meter.create_counter(
            name="agentops.session.errors",
            unit="error",
            description="Number of errors encountered during session"
        )
        
        self.api_counter = self.meter.create_counter(
            name="agentops.session.api.calls",
            unit="call",
            description="Number of external API calls made during session"
        )
        
        # Define mapping of span attributes to counter increment functions
        self.attribute_handlers = {
            # LLM spans
            SpanAttributes.LLM_REQUEST_TYPE: {
                LLMRequestTypeValues.CHAT.value: self._count_llm,
                LLMRequestTypeValues.COMPLETION.value: self._count_llm,
                LLMRequestTypeValues.EMBEDDING.value: self._count_api,
            },
            # Custom span attributes for other event types
            "span.kind": {
                "tool": self._count_tool,
                "action": self._count_action,
                "api": self._count_api,
            },
        }
        
        # Initialize cached event counts for backward compatibility
        self.event_counts = {
            "llms": 0,
            "tools": 0,
            "actions": 0,
            "errors": 0,
            "apis": 0
        }
    
    def on_end(self, span: ReadableSpan) -> None:
        """Process the span when it ends.
        
        Args:
            span: The span that ended.
        """
        # Process the span to determine its kind and increment the appropriate counter
        self._process_span(span)
        
        # Call the parent class's on_end method to continue normal processing
        super().on_end(span)
    
    def _process_span(self, span: ReadableSpan) -> None:
        """Process a span and increment the appropriate counter based on its attributes.
        
        Args:
            span: The span to process.
        """
        if not span:
            return
            
        # Check for error status
        if hasattr(span, "status") and span.status.is_error:
            self._count_error()
            return
            
        # Check span attributes against handlers
        for attr_key, attr_value_handlers in self.attribute_handlers.items():
            span_attr_value = span.attributes.get(attr_key)
            if span_attr_value in attr_value_handlers:
                attr_value_handlers[span_attr_value]()
                return
    
    def _count_llm(self):
        """Increment LLM call counter."""
        self.llm_counter.add(1, {"session_id": self.session_id})
        self.event_counts["llms"] += 1
    
    def _count_tool(self):
        """Increment tool call counter."""
        self.tool_counter.add(1, {"session_id": self.session_id})
        self.event_counts["tools"] += 1
    
    def _count_action(self):
        """Increment action counter."""
        self.action_counter.add(1, {"session_id": self.session_id})
        self.event_counts["actions"] += 1
    
    def _count_error(self):
        """Increment error counter."""
        self.error_counter.add(1, {"session_id": self.session_id})
        self.event_counts["errors"] += 1
    
    def _count_api(self):
        """Increment API call counter."""
        self.api_counter.add(1, {"session_id": self.session_id})
        self.event_counts["apis"] += 1
