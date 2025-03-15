"""
AgentOps Instrumentor for OpenAI Agents SDK

This module provides automatic instrumentation for the OpenAI Agents SDK when AgentOps is imported.
It implements a clean, maintainable implementation that follows semantic conventions.

IMPORTANT DISTINCTION BETWEEN OPENAI API FORMATS:
1. OpenAI Completions API - The traditional API format using prompt_tokens/completion_tokens
2. OpenAI Response API - The newer format used by the Agents SDK using input_tokens/output_tokens
3. Agents SDK - The framework that uses Response API format

The Agents SDK uses the Response API format, which we handle using shared utilities from
agentops.instrumentation.openai.
"""
from typing import Any

# AgentOps imports - only import what we actually use
from agentops.semconv import (
    CoreAttributes,
    WorkflowAttributes,
    InstrumentationAttributes,
    AgentAttributes,
    SpanAttributes,
)
from agentops.logging import logger
from agentops.helpers.serialization import safe_serialize, model_to_dict

# Import shared OpenAI instrumentation utilities
from agentops.instrumentation.openai import process_token_usage, process_token_details

# Version
__version__ = "0.1.0"

# Import the actual implementation
from .exporter import AgentsDetailedExporter


def get_model_info(agent: Any, run_config: Any = None) -> dict:
    """Extract model information from agent and run_config."""
    result = {"model_name": "unknown"}

    # First check run_config.model (highest priority)
    if run_config and hasattr(run_config, "model") and run_config.model:
        if isinstance(run_config.model, str):
            result["model_name"] = run_config.model
        elif hasattr(run_config.model, "model") and run_config.model.model:
            # For Model objects that have a model attribute
            result["model_name"] = run_config.model.model

    # Then check agent.model if we still have unknown
    if result["model_name"] == "unknown" and hasattr(agent, "model") and agent.model:
        if isinstance(agent.model, str):
            result["model_name"] = agent.model
        elif hasattr(agent.model, "model") and agent.model.model:
            # For Model objects that have a model attribute
            result["model_name"] = agent.model.model

    # Check for default model from OpenAI provider
    if result["model_name"] == "unknown":
        # Try to import the default model from the SDK
        try:
            from agents.models.openai_provider import DEFAULT_MODEL
            result["model_name"] = DEFAULT_MODEL
        except ImportError:
            pass

    # Extract model settings from agent
    if hasattr(agent, "model_settings") and agent.model_settings:
        model_settings = agent.model_settings

        # Extract model parameters
        for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
            if hasattr(model_settings, param) and getattr(model_settings, param) is not None:
                result[param] = getattr(model_settings, param)

    # Override with run_config.model_settings if available
    if run_config and hasattr(run_config, "model_settings") and run_config.model_settings:
        model_settings = run_config.model_settings

        # Extract model parameters
        for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
            if hasattr(model_settings, param) and getattr(model_settings, param) is not None:
                result[param] = getattr(model_settings, param)

    return result

