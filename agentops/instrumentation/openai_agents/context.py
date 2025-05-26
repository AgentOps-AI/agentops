"""
Context variables for OpenAI Agents instrumentation.
"""
import contextvars

full_prompt_contextvar = contextvars.ContextVar("agentops_full_prompt_context", default=None)
