"""OpenAI API instrumentation for AgentOps.

This package provides OpenTelemetry-based instrumentation for OpenAI API calls,
extending the third-party instrumentation to add support for OpenAI responses.
"""

from agentops.instrumentation.openai.instrumentor import OpenAIInstrumentor

__all__ = ["OpenAIInstrumentor"]