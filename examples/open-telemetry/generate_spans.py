from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import time
import jwt
from datetime import datetime, timedelta

# Generate test JWT token
def generate_test_token():
    payload = {
        "organization_id": "11111111-1111-1111-1111-111111111111",
        "user_id": "22222222-2222-2222-2222-222222222222",
        "exp": datetime.utcnow() + timedelta(days=1)
    }
    return jwt.encode(payload, "development-secret", algorithm="HS256")

# Initialize tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure OTLP exporter
otlp_exporter = OTLPSpanExporter(
    endpoint="http://localhost:4317",
    headers={
        "jwt": generate_test_token(),
        "api_key": "test-api-key"
    }
)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Generate test spans
with tracer.start_as_current_span("parent") as parent:
    parent.set_attribute("custom.attribute", "test-value")
    parent.set_attribute("jwt", generate_test_token())
    parent.set_attribute("api_key", "test-api-key")
    
    with tracer.start_as_current_span("child") as child:
        child.set_attribute("another.attribute", "child-value")
        child.set_attribute("jwt", generate_test_token())
        child.set_attribute("api_key", "test-api-key")
        time.sleep(0.1)  # Simulate some work

print("Test spans generated!") 