"""Semantic conventions for AgentOps spans"""
# Time attributes
TIME_START = "time.start"
TIME_END = "time.end"

# Common attributes (from Event base class)
EVENT_ID = "event.id"
EVENT_TYPE = "event.type"
EVENT_DATA = "event.data"
EVENT_START_TIME = "event.start_time"
EVENT_END_TIME = "event.end_time"
EVENT_PARAMS = "event.params"
EVENT_RETURNS = "event.returns"

# Session attributes
SESSION_ID = "session.id"
SESSION_TAGS = "session.tags"

# Agent attributes
AGENT_ID = "agent.id"

# Thread attributes
THREAD_ID = "thread.id"

# Error attributes
ERROR = "error"
ERROR_TYPE = "error.type"
ERROR_MESSAGE = "error.message"
ERROR_STACKTRACE = "error.stacktrace"
ERROR_DETAILS = "error.details"
ERROR_CODE = "error.code"
TRIGGER_EVENT_ID = "trigger_event.id"
TRIGGER_EVENT_TYPE = "trigger_event.type"

# LLM attributes
LLM_MODEL = "llm.model"
LLM_PROMPT = "llm.prompt"
LLM_COMPLETION = "llm.completion"
LLM_TOKENS_TOTAL = "llm.tokens.total"
LLM_TOKENS_PROMPT = "llm.tokens.prompt"
LLM_TOKENS_COMPLETION = "llm.tokens.completion"
LLM_COST = "llm.cost"

# Action attributes
ACTION_TYPE = "action.type"
ACTION_PARAMS = "action.params"
ACTION_RESULT = "action.result"
ACTION_LOGS = "action.logs"
ACTION_SCREENSHOT = "action.screenshot"

# Tool attributes
TOOL_NAME = "tool.name"
TOOL_PARAMS = "tool.params"
TOOL_RESULT = "tool.result"
TOOL_LOGS = "tool.logs"

# Execution attributes
EXECUTION_START_TIME = "execution.start_time"
EXECUTION_END_TIME = "execution.end_time"
