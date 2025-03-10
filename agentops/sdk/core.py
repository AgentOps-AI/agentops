from __future__ import annotations

import atexit
import threading
from typing import Dict, List, Optional, Set, Type, Union

from opentelemetry import context, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanProcessor
from opentelemetry.trace import Span

from agentops.config import Config
from agentops.logging import logger
from agentops.session.processors import LiveSpanProcessor
from agentops.sdk.spanned import SpannedBase
from agentops.sdk.factory import SpanFactory

class ImmediateExportProcessor(SpanProcessor):
    """
    Span processor that exports spans immediately when they are started.
    
    This processor is used for spans that need to be visible in real-time,
    even before they are completed.
    """
    
    def __init__(self, exporter):
        self._exporter = exporter
        self._lock = threading.Lock()
    
    def on_start(self, span: ReadableSpan, parent_context=None) -> None:
        """
        Called when a span starts. Exports the span immediately if it has the
        'export.immediate' attribute set to True.
        
        Args:
            span: The span that is starting
            parent_context: The parent context for the span
        """
        # Check if this span should be exported immediately
        if span.attributes.get('export.immediate', False):
            try:
                # Create a shallow copy of the span for export
                # This is necessary because the span is still in progress
                # and we don't want to export it as completed
                self._exporter.export([span])
                logger.debug(f"Immediately exported span: {span.name}")
            except Exception as e:
                logger.warning(f"Error exporting span immediately: {e}")
    
    def on_end(self, span: ReadableSpan) -> None:
        """
        Called when a span ends. We still need to export it again when it ends
        to capture the complete span data.
        
        Args:
            span: The span that is ending
        """
        try:
            self._exporter.export([span])
        except Exception as e:
            logger.warning(f"Error exporting span on end: {e}")
    
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush the exporter."""
        try:
            return self._exporter.force_flush(timeout_millis)
        except Exception as e:
            logger.warning(f"Error flushing exporter: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown the processor."""
        self._exporter.shutdown()


class TracingCore:
    """
    Central component for tracing in AgentOps.
    
    This class manages the creation, processing, and export of spans.
    It handles provider management, span creation, and context propagation.
    """
    
    _instance: Optional[TracingCore] = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> TracingCore:
        """Get the singleton instance of TracingCore."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize the tracing core."""
        self._provider = None
        self._processors: List[SpanProcessor] = []
        self._immediate_processor = None
        self._initialized = False
        self._config = None
        
        # Register shutdown handler
        atexit.register(self.shutdown)
    
    def initialize(self, config: Config) -> None:
        """
        Initialize the tracing core with the given configuration.
        
        Args:
            config: Configuration for tracing
        """
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            self._config = config
            
            # Create provider
            self._provider = TracerProvider(
                resource=Resource({SERVICE_NAME: "agentops"})
            )
            
            # Set as global provider
            trace.set_tracer_provider(self._provider)
            
            # Add processors
            if config.processor is not None:
                # Use custom processor
                self._provider.add_span_processor(config.processor)
                self._processors.append(config.processor)
            elif config.exporter is not None:
                # Use custom exporter with LiveSpanProcessor
                processor = LiveSpanProcessor(
                    config.exporter,
                    max_export_batch_size=config.max_queue_size,
                    schedule_delay_millis=config.max_wait_time,
                )
                self._provider.add_span_processor(processor)
                self._processors.append(processor)
                
                # Add immediate export processor using the same exporter
                self._immediate_processor = ImmediateExportProcessor(config.exporter)
                self._provider.add_span_processor(self._immediate_processor)
                self._processors.append(self._immediate_processor)
            else:
                # Use default processor and exporter
                endpoint = (
                    config.exporter_endpoint
                    if config.exporter_endpoint
                    else "https://otlp.agentops.cloud/v1/traces"
                )
                exporter = OTLPSpanExporter(endpoint=endpoint)
                
                # Regular processor for normal spans
                processor = LiveSpanProcessor(
                    exporter,
                    max_export_batch_size=config.max_queue_size,
                    schedule_delay_millis=config.max_wait_time,
                )
                self._provider.add_span_processor(processor)
                self._processors.append(processor)
                
                # Immediate processor for spans that need immediate export
                self._immediate_processor = ImmediateExportProcessor(exporter)
                self._provider.add_span_processor(self._immediate_processor)
                self._processors.append(self._immediate_processor)
            
            self._initialized = True
            logger.debug("Tracing core initialized")
    
    def shutdown(self) -> None:
        """Shutdown the tracing core."""
        if not self._initialized:
            return
        
        with self._lock:
            if not self._initialized:
                return
            
            # Flush processors
            for processor in self._processors:
                try:
                    processor.force_flush()
                except Exception as e:
                    logger.warning(f"Error flushing processor: {e}")
            
            # Shutdown provider
            if self._provider:
                try:
                    self._provider.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down provider: {e}")
            
            self._initialized = False
            logger.debug("Tracing core shutdown")
    
    def get_tracer(self, name: str = "agentops") -> trace.Tracer:
        """
        Get a tracer with the given name.
        
        Args:
            name: Name of the tracer
        
        Returns:
            A tracer with the given name
        """
        if not self._initialized:
            raise RuntimeError("Tracing core not initialized")
        
        return trace.get_tracer(name)
    
    def create_span(
        self,
        kind: str,
        name: str,
        parent: Optional[Union[SpannedBase, Span]] = None,
        attributes: Optional[Dict[str, any]] = None,
        auto_start: bool = True,
        immediate_export: bool = False,
        **kwargs
    ) -> SpannedBase:
        """
        Create a span of the specified kind.
        
        Args:
            kind: Kind of span (e.g., "session", "agent", "tool")
            name: Name of the span
            parent: Optional parent span or spanned object
            attributes: Optional attributes to set on the span
            auto_start: Whether to automatically start the span
            immediate_export: Whether to export the span immediately when started
            **kwargs: Additional keyword arguments to pass to the span constructor
        
        Returns:
            A new span of the specified kind
        """
        if not self._initialized:
            raise RuntimeError("Tracing core not initialized")
        
        # Add immediate export flag to attributes if needed
        if immediate_export:
            attributes = attributes or {}
            attributes['export.immediate'] = True
        
        return SpanFactory.create_span(
            kind=kind,
            name=name,
            parent=parent,
            attributes=attributes,
            auto_start=auto_start,
            immediate_export=immediate_export,
            **kwargs
        )
    
    def register_span_type(self, kind: str, span_class: Type[SpannedBase]) -> None:
        """
        Register a span type with the factory.
        
        Args:
            kind: Kind of span (e.g., "session", "agent", "tool")
            span_class: Class to use for creating spans of this kind
        """
        SpanFactory.register_span_type(kind, span_class) 