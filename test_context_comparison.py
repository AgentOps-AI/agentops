#!/usr/bin/env python
"""
Test script to compare the old and new context management approaches.
"""
import time
from opentelemetry import trace, context as context_api
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from agentops.sdk.decorators import agent, task, operation
from agentops.sdk.core import TracingCore
from agentops.client.client import Client
from agentops.sdk.decorators.utility import (_get_current_span_info, _make_span,
                                            _finalize_span, _create_as_current_span)
from agentops.logging import logger

# Initialize tracing
client = Client()
client.init()

# Add a console exporter for local debugging
provider = trace.get_tracer_provider()
if hasattr(provider, "add_span_processor"):
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

def test_manual_context():
    """Test using the manual context management approach"""
    logger.debug("===== TESTING MANUAL CONTEXT APPROACH =====")
    
    # Create the root span
    root_span, root_ctx, root_token = _make_span("root", "test")
    logger.debug(f"Created root span: {_get_current_span_info()}")
    
    try:
        # Create a child span
        child_span, child_ctx, child_token = _make_span("child", "test")
        logger.debug(f"Created child span: {_get_current_span_info()}")
        
        try:
            # Create a grandchild span
            grandchild_span, grandchild_ctx, grandchild_token = _make_span("grandchild", "test")
            logger.debug(f"Created grandchild span: {_get_current_span_info()}")
            
            # Do some work
            time.sleep(0.1)
            
            # End the grandchild span
            _finalize_span(grandchild_span, grandchild_token)
            logger.debug(f"After ending grandchild span: {_get_current_span_info()}")
        
        finally:
            # End the child span
            _finalize_span(child_span, child_token)
            logger.debug(f"After ending child span: {_get_current_span_info()}")
    
    finally:
        # End the root span
        _finalize_span(root_span, root_token)
        logger.debug(f"After ending root span: {_get_current_span_info()}")

def test_context_manager():
    """Test using the context manager approach"""
    logger.debug("===== TESTING CONTEXT MANAGER APPROACH =====")
    
    # Get a tracer
    tracer = TracingCore.get_instance().get_tracer()
    
    # Create spans using context manager (native OpenTelemetry approach)
    with _create_as_current_span("root", "test") as root_span:
        logger.debug(f"Created root span: {_get_current_span_info()}")
        
        with _create_as_current_span("child", "test") as child_span:
            logger.debug(f"Created child span: {_get_current_span_info()}")
            
            with _create_as_current_span("grandchild", "test") as grandchild_span:
                logger.debug(f"Created grandchild span: {_get_current_span_info()}")
                
                # Do some work
                time.sleep(0.1)
            
            logger.debug(f"After grandchild span: {_get_current_span_info()}")
        
        logger.debug(f"After child span: {_get_current_span_info()}")
    
    logger.debug(f"After root span: {_get_current_span_info()}")

if __name__ == "__main__":
    # Test both approaches
    test_manual_context()
    test_context_manager()
    
    # Give the batch processor time to export
    time.sleep(1) 