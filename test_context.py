#!/usr/bin/env python
"""
Test script to debug OpenTelemetry context propagation issues.
"""
import time
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from agentops.sdk.decorators import agent, task, operation
from agentops.sdk.core import TracingCore
from agentops.client.client import Client
from agentops.sdk.decorators.utility import _get_current_span_info
from agentops.logging import logger

# Initialize tracing
client = Client()  # Use default initialization
client.init()  # This should set up TracingCore

# Add a console exporter for local debugging
provider = trace.get_tracer_provider()
if hasattr(provider, "add_span_processor"):
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

@agent
def my_agent():
    """Test agent function that should create a parent span"""
    logger.debug(f"In my_agent - current span: {_get_current_span_info()}")
    
    # Call the task inside the agent
    result = my_task()
    
    # Also explicitly call operation with a context manager
    tracer = TracingCore.get_instance().get_tracer()
    with tracer.start_as_current_span("manual_operation") as manual_span:
        manual_span.set_attribute("manual", True)
        logger.debug(f"In manual operation - current span: {_get_current_span_info()}")
        time.sleep(0.1)
    
    return result

@task
def my_task():
    """Test task function that should create a child span under the agent span"""
    logger.debug(f"In my_task - current span: {_get_current_span_info()}")
    
    # Call a nested operation
    return my_operation()

@operation
def my_operation():
    """Test operation that should be nested under the task span"""
    logger.debug(f"In my_operation - current span: {_get_current_span_info()}")
    time.sleep(0.1)
    return "done"

if __name__ == "__main__":
    # Run the test
    result = my_agent()
    print(f"Result: {result}")
    
    # Give the batch processor time to export
    time.sleep(1) 