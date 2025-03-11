from opentelemetry import trace
from agentops.sdk.decorators import session, agent, tool

@session(name="example_session", tags=["example", "demo"])
class SessionExample:
    def __init__(self):
        print("Session initialized")
        # The session span is available as self._session_span
        print(f"Session ID: {self._session_span.span_id}")
    
    @agent(name="example_agent", agent_type="assistant")
    def run_agent(self):
        print("Agent running")
        # Access session directly from class instance
        print(f"Agent's session: {self._session_span.name}")
        
        # Call a tool
        self.use_tool("sample input")
        
        # Call an external function
        external_function()
    
    @tool(name="example_tool", tool_type="utility")
    def use_tool(self, input_data):
        print(f"Tool running with input: {input_data}")
        
        # Get session from class instance
        print(f"Tool's session (from instance): {self._session_span.name}")

def external_function():
    """A function outside the class hierarchy."""
    print("External function running")
    
    # Get current span (not the session span)
    current_span = trace.get_current_span()
    print(f"Current span in external function: {current_span}")
    
    # NOTE: With current implementation, we can't get back to the session span
    # from here without additional code

if __name__ == "__main__":
    # Create and use the session
    example = SessionExample()
    example.run_agent() 