import pytest
from agentops.event import ActionEvent, ErrorEvent, LLMEvent, ToolEvent

@pytest.fixture
def mock_llm_event():
    """Creates an LLMEvent for testing"""
    return LLMEvent(
        prompt="What is the meaning of life?",
        completion="42",
        model="gpt-4",
        prompt_tokens=10,
        completion_tokens=1,
        cost=0.01,
    )

@pytest.fixture
def mock_action_event():
    """Creates an ActionEvent for testing"""
    return ActionEvent(
        action_type="process_data",
        params={"input_file": "data.csv"},
        returns="100 rows processed",
        logs="Successfully processed all rows",
    )

@pytest.fixture
def mock_tool_event():
    """Creates a ToolEvent for testing"""
    return ToolEvent(
        name="searchWeb",
        params={"query": "python testing"},
        returns=["result1", "result2"],
        logs={"status": "success"},
    )

@pytest.fixture
def mock_error_event():
    """Creates an ErrorEvent for testing"""
    trigger = ActionEvent(action_type="risky_action")
    error = ValueError("Something went wrong")
    return ErrorEvent(
        trigger_event=trigger,
        exception=error,
        error_type="ValueError",
        details="Detailed error info"
    )
