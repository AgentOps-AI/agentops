# This example shows how to monkey patch the SessionSpan class
# to add session tracking functionality

from agentops.sdk.spans.session import SessionSpan

# Store the original start and end methods
original_start = SessionSpan.start
original_end = SessionSpan.end

# Create a global registry
SESSION_REGISTRY = {}

# Patch the start method to register the session
def patched_start(self):
    # Call the original start method
    result = original_start(self)
    
    # Register the session
    if self.span:
        trace_id = self.span.get_span_context().trace_id
        SESSION_REGISTRY[trace_id] = self
    
    return result

# Patch the end method to unregister the session
def patched_end(self, state="SUCCEEDED"):
    # Call the original end method
    result = original_end(self, state)
    
    # Unregister the session
    if self.span:
        trace_id = self.span.get_span_context().trace_id
        if trace_id in SESSION_REGISTRY:
            del SESSION_REGISTRY[trace_id]
    
    return result

# Add a function to get the current session
def get_current_session():
    from opentelemetry import trace
    current_span = trace.get_current_span()
    if current_span:
        trace_id = current_span.get_span_context().trace_id
        return SESSION_REGISTRY.get(trace_id)
    return None

# Apply the patches
SessionSpan.start = patched_start
SessionSpan.end = patched_end 