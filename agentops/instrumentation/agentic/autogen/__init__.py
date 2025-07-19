"""AutoGen Instrumentation Module

This module provides instrumentation for the original AutoGen framework (autogen_agentchat).
It creates create_agent spans that match the expected trace structure for AutoGen agents.

"""

from agentops.instrumentation.common import LibraryInfo

# Library information
_library_info = LibraryInfo(name="autogen_agentchat")
LIBRARY_NAME = _library_info.name
LIBRARY_VERSION = _library_info.version

# Import after defining constants to avoid circular imports
from .instrumentor import AutoGenInstrumentor

# Import modular components for advanced users
from .agents import (
    BaseChatAgentInstrumentor,
    AssistantAgentInstrumentor,
    UserProxyAgentInstrumentor,
    CodeExecutorAgentInstrumentor,
    SocietyOfMindAgentInstrumentor,
)
from .teams import (
    RoundRobinGroupChatInstrumentor,
    SelectorGroupChatInstrumentor,
    SwarmInstrumentor,
)
from .utils import (
    AutoGenSpanManager,
    extract_agent_attributes,
    safe_str,
    safe_extract_content,
    create_agent_span,
    instrument_async_generator,
    instrument_coroutine,
)

__all__ = [
    # Main instrumentors
    "AutoGenInstrumentor",
    
    # Library info
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    
    # Agent instrumentors
    "BaseChatAgentInstrumentor",
    "AssistantAgentInstrumentor", 
    "UserProxyAgentInstrumentor",
    "CodeExecutorAgentInstrumentor",
    "SocietyOfMindAgentInstrumentor",
    
    # Team instrumentors
    "RoundRobinGroupChatInstrumentor",
    "SelectorGroupChatInstrumentor",
    "SwarmInstrumentor",
    
    # Utilities
    "AutoGenSpanManager",
    "extract_agent_attributes",
    "safe_str",
    "safe_extract_content", 
    "create_agent_span",
    "instrument_async_generator",
    "instrument_coroutine",
] 
