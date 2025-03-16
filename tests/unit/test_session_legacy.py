

def test_session_auto_start(instrumentation):
    import agentops
    from agentops.legacy import Session

    # Pass a dummy API key for the test
    session = agentops.init(api_key="test-api-key", auto_start_session=True)
    
    assert isinstance(session, Session)


def test_crewai_backwards_compatibility(instrumentation):
    """
    CrewAI needs to access:

    agentops.track_agent
    agentops.track_tool
    agentops.start_session
    agentops.end_session
    agentops.ActionEvent
    agentops.ToolEvent
    """
    import agentops
    from agentops.legacy import Session

    # Test initialization with API key
    agentops.init(api_key="test-api-key")

    # Test session management functions
    session = agentops.start_session(tags=["test", "crewai"])
    assert isinstance(session, Session)

    # Test that passing a string to end_session doesn't raise an error
    agentops.end_session("Success")  # This pattern is used in CrewAI

    # Test track_agent function exists and doesn't raise errors
    try:
        # Mock an agent object similar to what CrewAI would provide
        class MockAgent:
            def __init__(self):
                self.role = "Test Agent"
                self.goal = "Testing"
                self.id = "test-agent-id"
        
        agent = MockAgent()
        agentops.track_agent(agent)
    except Exception as e:
        assert False, f"track_agent raised an exception: {e}"
        
    # Test track_tool function exists and doesn't raise errors
    try:
        # Mock a tool object similar to what CrewAI would provide
        class MockTool:
            def __init__(self):
                self.name = "Test Tool"
                self.description = "A test tool"
        
        tool = MockTool()
        agentops.track_tool(tool, "Test Agent")
    except Exception as e:
        assert False, f"track_tool raised an exception: {e}"

    # Test events that CrewAI might use
    tool_event = agentops.ToolEvent(name="test_tool")
    action_event = agentops.ActionEvent(action_type="test_action")
    
    # Verify that record function works with these events
    agentops.record(tool_event)
    agentops.record(action_event)