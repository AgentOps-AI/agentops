"""Metrics for OpenTelemetry semantic conventions."""


class Meters:
    # Gen AI metrics (OpenTelemetry standard)
    LLM_GENERATION_CHOICES = "gen_ai.client.generation.choices"
    LLM_TOKEN_USAGE = "gen_ai.client.token.usage"
    LLM_OPERATION_DURATION = "gen_ai.client.operation.duration"

    # OpenAI specific metrics
    LLM_COMPLETIONS_EXCEPTIONS = "gen_ai.openai.chat_completions.exceptions"
    LLM_STREAMING_TIME_TO_FIRST_TOKEN = "gen_ai.openai.chat_completions.streaming_time_to_first_token"
    LLM_STREAMING_TIME_TO_GENERATE = "gen_ai.openai.chat_completions.streaming_time_to_generate"
    LLM_EMBEDDINGS_EXCEPTIONS = "gen_ai.openai.embeddings.exceptions"
    LLM_EMBEDDINGS_VECTOR_SIZE = "gen_ai.openai.embeddings.vector_size"
    LLM_IMAGE_GENERATIONS_EXCEPTIONS = "gen_ai.openai.image_generations.exceptions"

    # Anthropic specific metrics
    LLM_ANTHROPIC_COMPLETION_EXCEPTIONS = "gen_ai.anthropic.completion.exceptions"

    # Agent metrics
    AGENT_RUNS = "gen_ai.agent.runs"
    AGENT_TURNS = "gen_ai.agent.turns"
    AGENT_EXECUTION_TIME = "gen_ai.agent.execution_time"
