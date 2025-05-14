"""Semantic conventions for LangChain instrumentation."""


class LangChainAttributeValues:
    """Standard values for LangChain attributes."""

    CHAIN_KIND_SEQUENTIAL = "sequential"
    CHAIN_KIND_LLM = "llm"
    CHAIN_KIND_ROUTER = "router"

    # Chat message roles
    ROLE_SYSTEM = "system"
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_FUNCTION = "function"
    ROLE_TOOL = "tool"


class LangChainAttributes:
    """
    Attributes for LangChain instrumentation.

    Note: LLM-specific attributes are derived from SpanAttributes to maintain
    consistency across instrumentations.
    """

    # Session attributes
    SESSION_TAGS = "langchain.session.tags"

    LLM_NAME = "langchain.llm.name"
    LLM_MODEL = "langchain.llm.model"

    # Chain attributes - specific to LangChain
    CHAIN_NAME = "langchain.chain.name"
    CHAIN_TYPE = "langchain.chain.type"
    CHAIN_ERROR = "langchain.chain.error"
    CHAIN_KIND = "langchain.chain.kind"
    CHAIN_VERBOSE = "langchain.chain.verbose"

    # Agent attributes - specific to LangChain agents
    AGENT_ACTION_LOG = "langchain.agent.action.log"
    AGENT_ACTION_INPUT = "langchain.agent.action.input"
    AGENT_ACTION_TOOL = "langchain.agent.action.tool"
    AGENT_FINISH_RETURN_VALUES = "langchain.agent.finish.return_values"
    AGENT_FINISH_LOG = "langchain.agent.finish.log"

    # Tool attributes - specific to LangChain tools
    TOOL_NAME = "langchain.tool.name"
    TOOL_INPUT = "langchain.tool.input"
    TOOL_OUTPUT = "langchain.tool.output"
    TOOL_DESCRIPTION = "langchain.tool.description"
    TOOL_ERROR = "langchain.tool.error"
    TOOL_ARGS_SCHEMA = "langchain.tool.args_schema"
    TOOL_RETURN_DIRECT = "langchain.tool.return_direct"

    # Chat attributes - specific to LangChain chat models
    CHAT_MESSAGE_ROLES = "langchain.chat_message.roles"
    CHAT_MODEL_TYPE = "langchain.chat_model.type"

    # Text callback attributes
    TEXT_CONTENT = "langchain.text.content"

    LLM_ERROR = "langchain.llm.error"
