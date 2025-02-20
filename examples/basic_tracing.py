from opentelemetry import trace
import agentops
from agentops.session import Session

def main():
    session = Session(tags=["demo", "basic-tracing"])
    
    # Tracer is ready immediately
    with session.tracer.start_operation("data_processing") as span:
        span.set_attribute("data.size", 1000)
        process_data()
        
    # Nested operations
    with session.tracer.start_operation("analysis") as analysis_span:
        analysis_span.set_attribute("analysis.type", "basic")
        
        with session.tracer.start_operation("sub_task") as sub_span:
            sub_span.set_attribute("sub_task.name", "validation")
            # More work...

def process_data():
    # Simulated work
    pass

if __name__ == "__main__":
    main() 
