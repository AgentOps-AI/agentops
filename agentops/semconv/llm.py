"""Attributes specific to LLM spans."""

class LLMAttributes:
    """Attributes specific to LLM spans."""
    
    # Request
    LLM_MODEL = "llm.model"                # Model name
    LLM_PROVIDER = "llm.provider"          # Provider (OpenAI, Anthropic, etc.)
    LLM_TEMPERATURE = "llm.temperature"    # Temperature setting
    LLM_MAX_TOKENS = "llm.max_tokens"      # Max tokens setting
    LLM_PROMPT = "llm.prompt"              # Prompt text
    
    # Response
    LLM_COMPLETION = "llm.completion"      # Completion text
    LLM_FINISH_REASON = "llm.finish_reason"  # Reason for finishing
    
    # Usage
    LLM_PROMPT_TOKENS = "llm.prompt_tokens"  # Prompt token count
    LLM_COMPLETION_TOKENS = "llm.completion_tokens"  # Completion token count
    LLM_TOTAL_TOKENS = "llm.total_tokens"  # Total token count
    
    # Cost
    LLM_COST = "llm.cost"                  # Cost of LLM call
