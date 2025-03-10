"""Metrics for OpenTelemetry semantic conventions."""

class Meters:
    LLM_GENERATION_CHOICES = "gen_ai.client.generation.choices"
    LLM_TOKEN_USAGE = "gen_ai.client.token.usage"
    LLM_OPERATION_DURATION = "gen_ai.client.operation.duration"
    LLM_COMPLETIONS_EXCEPTIONS = "llm.openai.chat_completions.exceptions"
    LLM_STREAMING_TIME_TO_FIRST_TOKEN = (
        "llm.openai.chat_completions.streaming_time_to_first_token"
    )
    LLM_STREAMING_TIME_TO_GENERATE = (
        "llm.openai.chat_completions.streaming_time_to_generate"
    )
    LLM_EMBEDDINGS_EXCEPTIONS = "llm.openai.embeddings.exceptions"
    LLM_EMBEDDINGS_VECTOR_SIZE = "llm.openai.embeddings.vector_size"
    LLM_IMAGE_GENERATIONS_EXCEPTIONS = "llm.openai.image_generations.exceptions"
    LLM_ANTHROPIC_COMPLETION_EXCEPTIONS = "llm.anthropic.completion.exceptions"