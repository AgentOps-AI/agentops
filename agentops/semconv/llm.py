"""Attributes specific to LLM spans."""

class LLMAttributes:
    """Attributes specific to LLM spans."""
    
    # Identity
    MODEL_NAME = "llm.model.name"          # Name of the LLM model
    
    # Usage metrics
    INPUT_TOKENS = "llm.usage.input_tokens"    # Number of input tokens
    OUTPUT_TOKENS = "llm.usage.output_tokens"  # Number of output tokens
    TOTAL_TOKENS = "llm.usage.total_tokens"    # Total number of tokens
    
    # Content
    PROMPT = "llm.prompt"                  # Prompt sent to the LLM
    COMPLETION = "llm.completion"          # Completion returned by the LLM
    INPUT = "llm.input"                  # Input sent to the LLM
    OUTPUT = "llm.output"                  # Output returned by the LLM
    
    # Request parameters
    TEMPERATURE = "llm.request.temperature"        # Temperature parameter
    TOP_P = "llm.request.top_p"                    # Top-p parameter
    MAX_TOKENS = "llm.request.max_tokens"          # Maximum tokens to generate
    FREQUENCY_PENALTY = "llm.request.frequency_penalty"  # Frequency penalty
    PRESENCE_PENALTY = "llm.request.presence_penalty"    # Presence penalty
    
    # Request metadata
    REQUEST_TYPE = "llm.request.type"              # Type of request (chat, completion, etc.)
    IS_STREAMING = "llm.request.is_streaming"      # Whether the request is streaming
    
    # Response metadata
    FINISH_REASON = "llm.response.finish_reason"   # Reason for finishing generation
    
    # System
    SYSTEM = "llm.system"                  # System message or context 