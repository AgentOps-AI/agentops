from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
import time

# Set up the tracer
provider = TracerProvider()
processor = SimpleSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

# Create and use a span
with tracer.start_as_current_span("test_operation") as span:
    # Do some work
    time.sleep(1)
    
    # Get span context
    span_context = span.get_span_context()
    breakpoint()
    
    # Print span details
    print(f"Span ID: {span_context.span_id:x}")
    print(f"Trace ID: {span_context.trace_id:x}")
    print(f"Start Time: {span.start_time}")
    print(f"Attributes: {span.attributes}")
    
    # Add some attributes
    span.set_attribute("custom.attribute", "test_value") 
