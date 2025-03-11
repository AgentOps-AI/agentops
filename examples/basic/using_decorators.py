import agentops

@agentops.start_session(tags=["foo", "bar"])
def foo():
    # Get the current session
    current_session = agentops.session.current
    # Use current_session here...
