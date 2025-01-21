import pytest
from agentops.partners.autogen_logger import AutogenLogger
from autogen import UserProxyAgent, AssistantAgent, register_function
import agentops


@pytest.fixture
def autogen_logger():
    """Fixture for AutogenLogger with auto start/stop."""
    logger = AutogenLogger()
    logger.start()
    yield logger
    logger.stop()


@pytest.fixture
def math_agents(openai_client, autogen_logger):
    """Math agent group with calculator tool and all configurations."""
    # Base configuration for all agents
    base_config = {
        "max_consecutive_auto_reply": 0,  # Disable auto-reply
        "code_execution_config": False,
        "llm_config": False,  # Disable LLM-based auto reply
    }

    # LLM configuration for math assistant
    llm_config = {
        "config_list": [
            {
                "model": "gpt-4",
                "api_key": openai_client.api_key,
                "timeout": 10,
            }
        ],
        "timeout": 10,
        "temperature": 0,  # Deterministic for testing
    }

    # Create user proxy agent
    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: "TERMINATE" in x.get("content", "") or x.get("content", "") == "",
        **base_config,
    )

    # Create assistant agent
    assistant = AssistantAgent(
        name="assistant",
        system_message="You are a math assistant. Use the calculator tool when needed. Return TERMINATE when done.",
        llm_config=llm_config,
        max_consecutive_auto_reply=1,
    )

    # Register agents with logger
    autogen_logger.log_new_agent(user_proxy, {})
    autogen_logger.log_new_agent(assistant, {})

    # Define calculator tool
    def calculator(a: int, b: int, operator: str) -> int:
        if operator == "+":
            return a + b
        elif operator == "-":
            return a - b
        elif operator == "*":
            return a * b
        elif operator == "/":
            return int(a / b)
        else:
            raise ValueError("Invalid operator")

    # Register calculator with both agents
    assistant.register_for_llm(name="calculator", description="A simple calculator")(calculator)

    user_proxy.register_for_execution(name="calculator")(calculator)

    # Register function between agents
    register_function(
        calculator, caller=assistant, executor=user_proxy, name="calculator", description="A simple calculator"
    )

    return user_proxy, assistant
