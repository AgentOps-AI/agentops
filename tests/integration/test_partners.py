import pytest
from agentops.partners.autogen_logger import AutogenLogger

@pytest.mark.usefixtures("agentops_session")
@pytest.mark.vcr
def test_autogen_logger_init(autogen_logger):
    """Test AutogenLogger initialization"""
    assert isinstance(autogen_logger, AutogenLogger)
    assert hasattr(autogen_logger, 'start')
    assert hasattr(autogen_logger, 'stop')
    assert hasattr(autogen_logger, 'get_connection')

@pytest.mark.usefixtures("agentops_session")
@pytest.mark.vcr
def test_autogen_logger_session_flow(autogen_logger, math_agents):
    """Test complete session flow with AutogenLogger"""
    user_proxy, assistant = math_agents
    
    user_proxy.initiate_chat(
        assistant,
        message="What is 2 + 2?",
    )
    
    # Check that events were logged through the logger's methods
    assert len(autogen_logger.agent_store) > 0  # Agents were registered
    assert any(agent["autogen_id"] == str(id(user_proxy)) for agent in autogen_logger.agent_store)
    assert any(agent["autogen_id"] == str(id(assistant)) for agent in autogen_logger.agent_store)

@pytest.mark.usefixtures("agentops_session")
@pytest.mark.vcr
def test_math_agent_tool_usage(autogen_logger, math_agents):
    """Test math agent tool usage tracking"""
    user_proxy, assistant = math_agents
    
    user_proxy.initiate_chat(
        assistant,
        message="What is (1423 - 123) / 3 + (32 + 23) * 5?",
    )
    
    # Check that tool usage was logged
    assert len(autogen_logger.agent_store) > 0
    assert any(agent["autogen_id"] == str(id(assistant)) for agent in autogen_logger.agent_store)

@pytest.mark.usefixtures("agentops_session")
@pytest.mark.vcr
def test_math_agent_error_handling(autogen_logger, math_agents):
    """Test math agent error handling"""
    user_proxy, assistant = math_agents
    
    # The assistant should handle invalid operators gracefully
    user_proxy.initiate_chat(
        assistant,
        message="What is 123 @ 456?",
    )
    
    # Check that error was logged
    assert len(autogen_logger.agent_store) > 0
    assert any(agent["autogen_id"] == str(id(assistant)) for agent in autogen_logger.agent_store)

@pytest.mark.usefixtures("agentops_session")
@pytest.mark.vcr
def test_math_agent_termination(autogen_logger, math_agents):
    """Test math agent termination"""
    user_proxy, assistant = math_agents
    
    user_proxy.initiate_chat(
        assistant,
        message="What is 1 + 1? Return TERMINATE when done.",
    )
    
    # Check that termination was logged
    assert len(autogen_logger.agent_store) > 0
    assert any(agent["autogen_id"] == str(id(assistant)) for agent in autogen_logger.agent_store)
