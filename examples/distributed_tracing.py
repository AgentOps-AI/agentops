import requests
from agentops.session import Session

def service_a():
    # First service initiates the session
    session = Session(tags=["service-a"])
    
    with session.tracer.start_operation("prepare_request") as span:
        # Prepare headers for context propagation
        headers = {}
        session.tracer.inject_context(headers)
        
        # Make request to service B
        response = requests.post(
            "http://service-b/process",
            headers=headers,
            json={"data": "example"}
        )
        
        span.set_attribute("http.status_code", response.status_code)

def service_b(headers, data):
    # Second service creates session with propagated context
    session = Session(tags=["service-b"])
    
    # Extract the propagated context
    context = session.tracer.extract_context(headers)
    
    with session.tracer.start_operation("process_request") as span:
        span.set_attribute("data.received", len(data))
        # Process the request...

# Example usage (normally these would be separate services)
if __name__ == "__main__":
    service_a() 