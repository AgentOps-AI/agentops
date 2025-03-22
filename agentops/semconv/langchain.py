"""Semantic conventions for LangChain instrumentation."""

from enum import Enum


class LangChainAttributeValues:
    """Standard values for LangChain attributes."""
    
    CHAIN_KIND_SEQUENTIAL = "sequential"
    CHAIN_KIND_LLM = "llm"
    CHAIN_KIND_ROUTER = "router"


class LangChainAttributes:
    """Attributes for LangChain instrumentation."""
    
    SESSION_TAGS = "langchain.session.tags"
    
    CHAIN_NAME = "langchain.chain.name"
    CHAIN_TYPE = "langchain.chain.type"
    CHAIN_ERROR = "langchain.chain.error"
    CHAIN_KIND = "langchain.chain.kind"
    CHAIN_VERBOSE = "langchain.chain.verbose"
    
    LLM_NAME = "langchain.llm.name"
    LLM_MODEL = "langchain.llm.model"
    LLM_PROVIDER = "langchain.llm.provider"
    LLM_TEMPERATURE = "langchain.llm.temperature"
    LLM_MAX_TOKENS = "langchain.llm.max_tokens"
    LLM_TOP_P = "langchain.llm.top_p"
    LLM_ERROR = "langchain.llm.error"
    
    AGENT_ACTION_LOG = "langchain.agent.action_log"
    AGENT_FINISH_RETURN_VALUES = "langchain.agent.finish.return_values"
    AGENT_FINISH_LOG = "langchain.agent.finish.log"
    AGENT_ACTION_LOG = "langchain.agent.action.log"
    AGENT_ACTION_INPUT = "langchain.agent.action.input"
    AGENT_FINISH_RETURN_VALUES = "langchain.agent.finish.return_values"
    AGENT_ACTION_TOOL = "langchain.agent.action.tool"
    
    TOOL_NAME = "langchain.tool.name"
    TOOL_INPUT = "langchain.tool.input"
    TOOL_OUTPUT = "langchain.tool.output"
    TOOL_DESCRIPTION = "langchain.tool.description"
    TOOL_ERROR = "langchain.tool.error"
    TOOL_ARGS_SCHEMA = "langchain.tool.args_schema"
    TOOL_RETURN_DIRECT = "langchain.tool.return_direct"
    
    MESSAGE_ROLE = "langchain.message.role"
    
    CHAT_MESSAGE_ROLES = "langchain.chat_message.roles"
    CHAT_MODEL_TYPE = "langchain.chat_model.type"
    
    TEXT_CONTENT = "langchain.text.content"