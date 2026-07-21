import json
from types import SimpleNamespace

from agentops.integration.callbacks.langchain.utils import get_completion_attributes
from agentops.semconv import MessageAttributes, SpanAttributes


def test_get_completion_attributes_serializes_text_generation():
    response = SimpleNamespace(generations=[[SimpleNamespace(text="Hello", generation_info={"finish_reason": "stop"})]])

    attributes = get_completion_attributes(response)

    assert attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] == "Hello"
    assert attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] == "assistant"
    assert attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] == "stop"
    assert SpanAttributes.LLM_COMPLETIONS not in attributes


def test_get_completion_attributes_serializes_structured_output_tool_call():
    message = SimpleNamespace(
        content="",
        type="ai",
        tool_calls=[
            {
                "id": "call_1",
                "type": "tool_call",
                "name": "Score",
                "args": {"score": 7, "reason": "clear answer"},
            }
        ],
        additional_kwargs={},
        response_metadata={"finish_reason": "tool_calls"},
    )
    response = SimpleNamespace(generations=[[SimpleNamespace(message=message, text="")]])

    attributes = get_completion_attributes(response)

    prefix = f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0"
    assert attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] == "assistant"
    assert attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] == "tool_calls"
    assert attributes[f"{prefix}.id"] == "call_1"
    assert attributes[f"{prefix}.type"] == "tool_call"
    assert attributes[f"{prefix}.name"] == "Score"
    assert json.loads(attributes[f"{prefix}.arguments"]) == {"score": 7, "reason": "clear answer"}
    assert MessageAttributes.COMPLETION_CONTENT.format(i=0) not in attributes


def test_get_completion_attributes_supports_openai_shaped_tool_calls():
    message = SimpleNamespace(
        content=None,
        type="ai",
        tool_calls=[],
        additional_kwargs={
            "tool_calls": [
                {
                    "id": "call_legacy",
                    "type": "function",
                    "function": {"name": "Score", "arguments": '{"score": 9}'},
                }
            ]
        },
        response_metadata={},
    )
    response = SimpleNamespace(generations=[[SimpleNamespace(message=message, text="")]])

    attributes = get_completion_attributes(response)

    prefix = f"{SpanAttributes.LLM_COMPLETIONS}.0.tool_calls.0"
    assert attributes[f"{prefix}.id"] == "call_legacy"
    assert attributes[f"{prefix}.type"] == "function"
    assert attributes[f"{prefix}.name"] == "Score"
    assert attributes[f"{prefix}.arguments"] == '{"score": 9}'
