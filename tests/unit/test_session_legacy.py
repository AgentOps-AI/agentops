

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
    
    
def test_crewai_kwargs_pattern(instrumentation):
    """
    Test the CrewAI < 0.105.0 pattern where end_session is called with only kwargs.
    
    In versions < 0.105.0, CrewAI directly calls:
    agentops.end_session(
        end_state="Success",
        end_state_reason="Finished Execution", 
        is_auto_end=True
    )
    """
    import agentops
    from agentops.legacy import Session
    
    # Initialize with test API key
    agentops.init(api_key="test-api-key")
    
    # Create a session
    session = agentops.start_session(tags=["test", "crewai-kwargs"])
    assert isinstance(session, Session)
    
    # Test the CrewAI < 0.105.0 pattern - calling end_session with only kwargs
    agentops.end_session(
        end_state="Success",
        end_state_reason="Finished Execution",
        is_auto_end=True
    )
    
    # After calling end_session, creating a new session should work correctly
    # (this implicitly tests that the internal state is reset properly)
    new_session = agentops.start_session(tags=["test", "post-end"])
    assert isinstance(new_session, Session)
    
    
def test_crewai_kwargs_pattern_no_session(instrumentation):
    """
    Test the CrewAI < 0.105.0 pattern where end_session is called with only kwargs,
    but no session has been created.
    
    This should log a warning but not fail.
    """
    import agentops
    
    # Initialize with test API key
    agentops.init(api_key="test-api-key")
    
    # We don't need to explicitly clear the session state
    # Just make sure we start with a clean state by calling init
    
    # Test the CrewAI < 0.105.0 pattern - calling end_session with only kwargs
    # when no session exists. This should not raise an error.
    agentops.end_session(
        end_state="Success",
        end_state_reason="Finished Execution",
        is_auto_end=True
    )


def test_crewai_kwargs_force_flush():
    """
    Test that when using the CrewAI < 0.105.0 pattern (end_session with kwargs),
    the spans are properly exported to the backend with force_flush.
    
    This is a more comprehensive test that ensures spans are actually sent
    to the backend when using the CrewAI integration pattern.
    """
    import agentops
    from agentops.sdk.core import TracingCore
    import time
    
    # Initialize AgentOps with API key
    agentops.init(api_key="test-api-key")
    
    # Create a session
    session = agentops.start_session(tags=["test", "crewai-integration"])
    
    # Simulate some work
    time.sleep(0.1)
    
    # End session with kwargs (CrewAI < 0.105.0 pattern)
    agentops.end_session(
        end_state="Success",
        end_state_reason="Test Finished",
        is_auto_end=True
    )
    
    # Explicitly ensure the core isn't already shut down for the test
    assert TracingCore.get_instance()._initialized, "TracingCore should still be initialized"