import agentops
from agentops.sdk.decorators import session

# Initialize AgentOps
agentops.init()

# Example: Using the session decorator with a class
@session(name="DataProcessor", tags=["data_processing", "example"])
class DataProcessor:
    def __init__(self, data_source):
        self.data_source = data_source
        print(f"DataProcessor initialized with source: {data_source}")
    
    def process(self):
        print(f"Processing data from {self.data_source}")
        # Simulate processing
        return f"Processed data from {self.data_source}"
    
    def get_session_info(self):
        # Access the session span that was automatically created
        session_span = self.get_session_span()
        return f"Session ID: {session_span.span.get_span_context().span_id}"

# Create an instance of the decorated class
processor = DataProcessor("database")

# Use the instance
result = processor.process()
print(result)

# Get session information
session_info = processor.get_session_info()
print(session_info) 