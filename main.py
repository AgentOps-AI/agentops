import agentops

# Initialize AgentOps (if not already done)
agentops.init()

# INCORRECT USAGE (causes the error):
# with agentops.trace("debug_test"):
#     print("This will cause an AttributeError")

# CORRECT USAGE - using start_trace as a context manager:
with agentops.start_trace("debug_test") as trace:
    print("This is the correct way to use AgentOps as a context manager")
    print(f"Trace context: {trace}")
    
    # Your code here
    result = "some operation"
    
    # The trace will automatically end when exiting the context

# Alternative: Manual start/end
trace_context = agentops.start_trace("manual_trace")
try:
    print("Manual trace management")
    # Your code here
finally:
    agentops.end_trace(trace_context)

# Using the @trace decorator (for functions):
@agentops.trace("function_trace")
def my_function():
    print("This function is decorated with @agentops.trace")
    return "function result"

# Call the decorated function
result = my_function()