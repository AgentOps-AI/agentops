from enum import Enum
SUPPRESS_LANGUAGE_MODEL_INSTRUMENTATION_KEY = "suppress_language_model_instrumentation"
class Meters:
    # Define your custom meters here
    LLM_GENERATION_CHOICES = "gen_ai.client.generation.choices"
    LLM_TOKEN_USAGE = "gen_ai.client.token.usage"
    LLM_OPERATION_DURATION = "gen_ai.client.operation.duration"
    LLM_COMPLETIONS_EXCEPTIONS = "llm.openai.chat_completions.exceptions"
    LLM_STREAMING_TIME_TO_FIRST_TOKEN = "llm.openai.chat_completions.streaming_time_to_first_token"
    LLM_STREAMING_TIME_TO_GENERATE = "llm.openai.chat_completions.streaming_time_to_generate"
    LLM_EMBEDDINGS_EXCEPTIONS = "llm.openai.embeddings.exceptions"
    LLM_EMBEDDINGS_VECTOR_SIZE = "llm.openai.embeddings.vector_size"
    LLM_ANTHROPIC_COMPLETION_EXCEPTIONS = "llm.anthropic.completion.exceptions"

class SpanAttributes:
    # Define your custom span attributes here
    LLM_SYSTEM = "gen_ai.system"
    LLM_REQUEST_MODEL = "gen_ai.request.model"
    LLM_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    LLM_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    LLM_REQUEST_TOP_P = "gen_ai.request.top_p"
    LLM_PROMPTS = "gen_ai.prompt"
    LLM_COMPLETIONS = "gen_ai.completion"
    LLM_RESPONSE_MODEL = "gen_ai.response.model"
    LLM_USAGE_COMPLETION_TOKENS = "gen_ai.usage.completion_tokens"
    LLM_USAGE_PROMPT_TOKENS = "gen_ai.usage.prompt_tokens"
    LLM_USAGE_TOTAL_TOKENS = "llm.usage.total_tokens"
    LLM_REQUEST_TYPE = "llm.request.type"
    LLM_FREQUENCY_PENALTY = "llm.frequency_penalty"
    LLM_PRESENCE_PENALTY = "llm.presence_penalty"
    LLM_IS_STREAMING = "llm.is_streaming"
    LLM_RESPONSE_FINISH_REASON = "llm.response.finish_reason"
    LLM_CONTENT_COMPLETION_CHUNK = "llm.content.completion.chunk"
    LLM_USER = "llm.user"
    
    # OpenAI specific
    LLM_OPENAI_API_BASE = "gen_ai.openai.api_base"
    
    # Haystack
    HAYSTACK_OPENAI_CHAT = "haystack.openai.chat"
    HAYSTACK_OPENAI_COMPLETION = "haystack.openai.completion"

    # LLM Workflows
    WORKFLOW_SPAN_KIND = "workflow.span.kind"
    ENTITY_NAME = "entity.name"
    ENTITY_PATH = "entity.path"
    ENTITY_INPUT = "entity.input"
    ENTITY_OUTPUT = "entity.output"
    
    # Tools and functions
    LLM_REQUEST_FUNCTIONS = "llm.request.functions"

class LLMRequestTypeValues(Enum):
    COMPLETION = "completion"
    CHAT = "chat"
    RERANK = "rerank"
    EMBEDDING = "embedding"
    UNKNOWN = "unknown"

class WorkflowSpanKindValues(Enum):
    WORKFLOW = "workflow"
    TASK = "task"
    AGENT = "agent"
    TOOL = "tool"
    UNKNOWN = "unknown"