from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from agentops.session import Session

def main():
    # Create a session with OTLP export to Jaeger
    session = Session(
        tags=["jaeger-demo"],
        otlp_endpoint="http://localhost:4318/v1/traces"  # Jaeger OTLP HTTP endpoint
    )
    
    # Perform some traced operations
    with session.tracer.start_operation("complex_operation") as span:
        span.set_attribute("operation.importance", "high")
        
        # Some nested operations
        for i in range(3):
            with session.tracer.start_operation(f"sub_operation_{i}") as sub_span:
                sub_span.set_attribute("iteration", i)
                # Simulate work...
                if i == 1:
                    # Add an event
                    sub_span.add_event("interesting_occurrence", {
                        "reason": "something happened",
                        "severity": "medium"
                    })

if __name__ == "__main__":
    main()
    # View traces at http://localhost:16686 