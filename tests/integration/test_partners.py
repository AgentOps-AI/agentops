import pytest
from agentops.partners.autogen_logger import AutogenLogger


@pytest.mark.usefixtures("agentops_session")
@pytest.mark.vcr
def test_autogen(autogen_logger, math_agents):
    """Test complete AutogenLogger integration with math agents"""
    # 1. Verify logger initialization
    assert isinstance(autogen_logger, AutogenLogger)
    assert hasattr(autogen_logger, "start")
    assert hasattr(autogen_logger, "stop")
    assert hasattr(autogen_logger, "get_connection")

    user_proxy, assistant = math_agents

    # 2. Test basic calculation and agent registration
    user_proxy.initiate_chat(
        assistant,
        message="What is 2 + 2?",
    )

    # Verify agent registration
    assert len(autogen_logger.agent_store) > 0
    assert any(agent["autogen_id"] == str(id(user_proxy)) for agent in autogen_logger.agent_store)
    assert any(agent["autogen_id"] == str(id(assistant)) for agent in autogen_logger.agent_store)

    # 3. Test complex calculation with tool usage
    user_proxy.initiate_chat(
        assistant,
        message="What is (1423 - 123) / 3 + (32 + 23) * 5?",
    )

    # Verify tool usage logging
    assert any(agent["autogen_id"] == str(id(assistant)) for agent in autogen_logger.agent_store)

    # 4. Test error handling
    user_proxy.initiate_chat(
        assistant,
        message="What is 123 @ 456?",
    )

    # Verify error logging
    assert any(agent["autogen_id"] == str(id(assistant)) for agent in autogen_logger.agent_store)

    # 5. Test termination
    user_proxy.initiate_chat(
        assistant,
        message="What is 1 + 1? Return TERMINATE when done.",
    )

    # Verify termination logging
    assert any(agent["autogen_id"] == str(id(assistant)) for agent in autogen_logger.agent_store)
