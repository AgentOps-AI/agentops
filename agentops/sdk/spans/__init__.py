# Import all span types for easy access
from agentops.sdk.spans.session import SessionSpan
from agentops.sdk.spans.agent import AgentSpan
from agentops.sdk.spans.tool import ToolSpan
from agentops.sdk.spans.llm import LLMSpan
from agentops.sdk.spans.custom import CustomSpan

__all__ = [
    "SessionSpan",
    "AgentSpan",
    "ToolSpan",
    "LLMSpan",
    "CustomSpan",
] 