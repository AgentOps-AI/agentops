"""
Context variables for OpenAI Agents instrumentation.
"""
import contextvars

full_prompt_contextvar = contextvars.ContextVar("agentops_full_prompt_context", default=None)
agent_name_contextvar = contextvars.ContextVar("agentops_agent_name_context", default=None)
agent_handoffs_contextvar = contextvars.ContextVar("agentops_agent_handoffs_context", default=None)
