from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import time

# Initialize tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure OTLP exporter
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Generate test spans
with tracer.start_as_current_span("parent") as parent:
    parent.set_attribute("custom.attribute", "test-value")
    
    with tracer.start_as_current_span("child") as child:
        child.set_attribute("another.attribute", "child-value")
        time.sleep(0.1)  # Simulate some work

print("Test spans generated!") 