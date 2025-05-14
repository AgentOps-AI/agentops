"""Span attributes for OpenTelemetry semantic conventions."""


class SpanAttributes:
    # Semantic Conventions for LLM requests based on OpenTelemetry Gen AI conventions
    # Refer to https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md
    #
    # TODO: There is an important deviation from the OpenTelemetry spec in our current implementation.
    # In our OpenAI instrumentation, we're mapping from source→target keys incorrectly in the _token_type function
    # in shared/__init__.py. According to our established pattern, mapping dictionaries should consistently use
    # target→source format (where keys are target attributes and values are source fields).
    #
    # Current implementation (incorrect):
    # def _token_type(token_type: str):
    #     if token_type == "prompt_tokens":  # source
    #         return "input"  # target
    #
    # Correct implementation should be:
    # token_type_mapping = {
    #     "input": "prompt_tokens",  # target → source
    #     "output": "completion_tokens"
    # }
    #
    # Then we have to adapt code using the function to handle the inverted mapping.

    # System
    LLM_SYSTEM = "gen_ai.system"

    # Request attributes
    LLM_REQUEST_MODEL = "gen_ai.request.model"
    LLM_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    LLM_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    LLM_REQUEST_TOP_P = "gen_ai.request.top_p"
    LLM_REQUEST_TOP_K = "gen_ai.request.top_k"
    LLM_REQUEST_SEED = "gen_ai.request.seed"
    LLM_REQUEST_SYSTEM_INSTRUCTION = "gen_ai.request.system_instruction"
    LLM_REQUEST_CANDIDATE_COUNT = "gen_ai.request.candidate_count"
    LLM_REQUEST_STOP_SEQUENCES = "gen_ai.request.stop_sequences"
    LLM_REQUEST_TYPE = "gen_ai.request.type"
    LLM_REQUEST_STREAMING = "gen_ai.request.streaming"
    LLM_REQUEST_FREQUENCY_PENALTY = "gen_ai.request.frequency_penalty"
    LLM_REQUEST_PRESENCE_PENALTY = "gen_ai.request.presence_penalty"
    LLM_REQUEST_FUNCTIONS = "gen_ai.request.functions"
    LLM_REQUEST_HEADERS = "gen_ai.request.headers"
    LLM_REQUEST_INSTRUCTIONS = "gen_ai.request.instructions"
    LLM_REQUEST_VOICE = "gen_ai.request.voice"
    LLM_REQUEST_SPEED = "gen_ai.request.speed"

    # Content
    LLM_PROMPTS = "gen_ai.prompt"
    LLM_COMPLETIONS = "gen_ai.completion"  # DO NOT SET THIS DIRECTLY
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
    LLM_USAGE_REASONING_TOKENS = "gen_ai.usage.reasoning_tokens"
    LLM_USAGE_STREAMING_TOKENS = "gen_ai.usage.streaming_tokens"

    # Message attributes
    # see ./message.py for message-related attributes

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

    # Operation attributes
    OPERATION_NAME = "operation.name"
    OPERATION_VERSION = "operation.version"
