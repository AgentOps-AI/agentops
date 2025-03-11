from opentelemetry import trace
from agentops.sdk.decorators import session, agent, tool
from agentops.sdk.spans.utils import get_root_span

def print_current_session():
    """Print information about the current session."""
    session_span = get_root_span()
    if session_span:
        print(f"Current session: {session_span.name} (ID: {session_span.span_id})")
    else:
        print("No active session found")

@session(name="outer_session", tags=["outer"])
class OuterSession:
    def __init__(self):
        print("Outer session initialized")
        print_current_session()
    
    @agent(name="outer_agent")
    def run(self):
        print("Running outer agent")
        print_current_session()
        
        # Create a nested session
        inner = InnerSession()
        inner.run()
        
        # After the inner session completes, we should be back in the outer session
        print("Back to outer session")
        print_current_session()

@session(name="inner_session", tags=["inner"])
class InnerSession:
    def __init__(self):
        print("Inner session initialized")
        print_current_session()
    
    @agent(name="inner_agent")
    def run(self):
        print("Running inner agent")
        print_current_session()
        
        # Call a tool
        self.use_tool("inner data")
    
    @tool(name="inner_tool")
    def use_tool(self, data):
        print(f"Using inner tool with data: {data}")
        print_current_session()

if __name__ == "__main__":
    # Create and run the outer session
    outer = OuterSession()
    outer.run() 