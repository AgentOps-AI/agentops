from opentelemetry import trace
from agentops.sdk.decorators import session, agent, tool
from agentops.sdk.spans.utils import get_root_span

# Define a utility function to get the root span (to be implemented in your SDK)
def get_session_info():
    """Utility function to get information about the current session."""
    session_span = get_root_span()
    if session_span:
        print(f"Current session: {session_span.name} (ID: {session_span.span_id})")
        print(f"Session state: {session_span.state}")
        print(f"Session tags: {session_span._tags}")
    else:
        print("No active session found")

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
        
        # Alternative: Get session using the utility function
        get_session_info()

def external_function():
    """A function outside the class hierarchy."""
    print("External function running")
    
    # Get session using the utility function
    get_session_info()

if __name__ == "__main__":
    # Create and use the session
    example = SessionExample()
    example.run_agent() 