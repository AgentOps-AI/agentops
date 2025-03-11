from agentops.sdk.core import TracingCore

# Extend TracingCore with session tracking
def patch_tracing_core():
    original_init = TracingCore.__init__
    
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        # Add a dictionary to track active sessions
        self._active_sessions = {}
    
    # Add method to register session spans
    def register_session_span(self, session_span):
        if session_span and session_span.span:
            trace_id = session_span.span.get_span_context().trace_id
            self._active_sessions[trace_id] = session_span
    
    # Add method to unregister session spans
    def unregister_session_span(self, session_span):
        if session_span and session_span.span:
            trace_id = session_span.span.get_span_context().trace_id
            if trace_id in self._active_sessions:
                del self._active_sessions[trace_id]
    
    # Add method to retrieve session spans
    def get_session_span_by_trace_id(self, trace_id):
        return self._active_sessions.get(trace_id)
    
    # Patch the TracingCore class
    TracingCore.__init__ = new_init
    TracingCore.register_session_span = register_session_span
    TracingCore.unregister_session_span = unregister_session_span
    TracingCore.get_session_span_by_trace_id = get_session_span_by_trace_id

# Call this before using TracingCore
patch_tracing_core() 