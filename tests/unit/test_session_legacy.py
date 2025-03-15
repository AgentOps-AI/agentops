

def test_session_auto_start(instrumentation):
    import agentops
    from agentops.legacy import Session

    session = agentops.init(auto_start_session=True)
    

    assert isinstance(session, Session)


def test_crewai_backwards_compatibility(instrumentation):
    """
    CrewAI needs to access:

    agentops.track_agent
    agentops.track_tool
    
    """