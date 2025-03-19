"""Semantic conventions for Langchain integration.

This module defines the semantic conventions used for Langchain spans and attributes
in OpenTelemetry traces. These conventions ensure consistent attribute naming
across the Langchain integration.
"""

class LangchainAttributes:
    """Semantic conventions for Langchain spans and attributes."""

    # Run identifiers
    RUN_ID = "langchain.run.id"
    PARENT_RUN_ID = "langchain.parent_run.id"
    TAGS = "langchain.tags"
    METADATA = "langchain.metadata"
    
    # Response attributes
    RESPONSE = "langchain.response"
    PROMPT_TOKENS = "langchain.prompt_tokens"
    COMPLETION_TOKENS = "langchain.completion_tokens"
    TOTAL_TOKENS = "langchain.total_tokens"
    
    # Chain attributes
    CHAIN_OUTPUTS = "langchain.chain.outputs"
    
    # Tool attributes
    TOOL_OUTPUT = "langchain.tool.output"
    TOOL_LOG = "langchain.tool.log"
    OUTPUTS = "langchain.outputs"
    
    # Retriever attributes
    RETRIEVER_DOCUMENTS = "langchain.retriever.documents"
    
    # Error attributes
    ERROR_TYPE = "langchain.error.type"
    ERROR_MESSAGE = "langchain.error.message"
    ERROR_DETAILS = "langchain.error.details" 