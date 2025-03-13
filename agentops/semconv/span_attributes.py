"""Span attributes for OpenTelemetry semantic conventions."""


class SpanAttributes:
    # Semantic Conventions for LLM requests based on OpenTelemetry Gen AI conventions
    # Refer to https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md

    # System
    LLM_SYSTEM = "gen_ai.system"

    # Request attributes
    LLM_REQUEST_MODEL = "gen_ai.request.model"
    LLM_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    LLM_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    LLM_REQUEST_TOP_P = "gen_ai.request.top_p"
    LLM_REQUEST_TYPE = "gen_ai.request.type"
    LLM_REQUEST_STREAMING = "gen_ai.request.streaming"
    LLM_REQUEST_FREQUENCY_PENALTY = "gen_ai.request.frequency_penalty"
    LLM_REQUEST_PRESENCE_PENALTY = "gen_ai.request.presence_penalty"
    LLM_REQUEST_FUNCTIONS = "gen_ai.request.functions"
    LLM_REQUEST_HEADERS = "gen_ai.request.headers"

    # Content
    LLM_PROMPTS = "gen_ai.prompt"
    LLM_COMPLETIONS = "gen_ai.completion"
    LLM_CONTENT_COMPLETION_CHUNK = "gen_ai.completion.chunk"

    # Response attributes
    LLM_RESPONSE_MODEL = "gen_ai.response.model"
    LLM_RESPONSE_FINISH_REASON = "gen_ai.response.finish_reason"
    LLM_RESPONSE_STOP_REASON = "gen_ai.response.stop_reason"
    LLM_RESPONSE_ID = "gen_ai.response.id"

    # Usage metrics
    LLM_USAGE_COMPLETION_TOKENS = "gen_ai.usage.completion_tokens"
    LLM_USAGE_PROMPT_TOKENS = "gen_ai.usage.prompt_tokens"
    LLM_USAGE_TOTAL_TOKENS = "gen_ai.usage.total_tokens"
    LLM_USAGE_CACHE_CREATION_INPUT_TOKENS = "gen_ai.usage.cache_creation_input_tokens"
    LLM_USAGE_CACHE_READ_INPUT_TOKENS = "gen_ai.usage.cache_read_input_tokens"

    # Token type
    LLM_TOKEN_TYPE = "gen_ai.token.type"

    # User
    LLM_USER = "gen_ai.user"

    # OpenAI specific
    LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT = "gen_ai.openai.system_fingerprint"
    LLM_OPENAI_API_BASE = "gen_ai.openai.api_base"
    LLM_OPENAI_API_VERSION = "gen_ai.openai.api_version"
    LLM_OPENAI_API_TYPE = "gen_ai.openai.api_type"

    # AgentOps specific attributes
    AGENTOPS_ENTITY_OUTPUT = "agentops.entity.output"
    AGENTOPS_ENTITY_INPUT = "agentops.entity.input"
    AGENTOPS_SPAN_KIND = "agentops.span.kind"
    AGENTOPS_ENTITY_NAME = "agentops.entity.name"
