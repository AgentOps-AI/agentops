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
import asyncio
import functools
import json
import logging
import time
from typing import Any, Collection, Optional, Union, Set

# OpenTelemetry imports
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer, SpanKind, Status, StatusCode, get_current_span
from opentelemetry.metrics import get_meter

# AgentOps imports
from agentops.semconv import (
    CoreAttributes,
    WorkflowAttributes,
    InstrumentationAttributes,
    AgentAttributes,
    SpanAttributes,
    Meters,
)
from agentops.logging import logger
from agentops.helpers.serialization import safe_serialize, filter_unjsonable, model_to_dict

# Import shared OpenAI instrumentation utilities
from agentops.instrumentation.openai import process_token_usage, process_token_details

# Version
__version__ = "0.1.0"

# Try to find the agents SDK version
agents_sdk_version = "unknown"

def get_agents_sdk_version() -> str:
    """
    Try to find the version of the agents SDK.
    
    TODO: Improve this to try harder to find the version by:
    1. Checking for agents.__version__
    2. Checking package metadata
    3. Using importlib.metadata if available
    
    Returns:
        The agents SDK version string or "unknown" if not found
    """
    global agents_sdk_version
    
    if agents_sdk_version != "unknown":
        return agents_sdk_version
        
    # Try to import agents and get the version
    try:
        import agents
        if hasattr(agents, '__version__'):
            agents_sdk_version = agents.__version__
            return agents_sdk_version
    except (ImportError, AttributeError):
        pass
    
    # For now, return unknown if we can't find it
    return agents_sdk_version

# Import after defining helpers to avoid circular imports
from .exporter import AgentsDetailedExporter


def safe_extract(obj: Any, attr_path: str, default: Any = None) -> Any:
    """Safely extract a nested attribute from an object using dot notation."""
    attrs = attr_path.split(".")
    current = obj
    
    try:
        for attr in attrs:
            if isinstance(current, dict):
                current = current.get(attr)
            else:
                current = getattr(current, attr, None)
            
            if current is None:
                return default
        return current
    except (AttributeError, KeyError):
        return default


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


def flush_active_streaming_operations(tracer_provider=None):
    """
    Manually flush spans for active streaming operations.
    
    This function can be called to force flush spans for active streaming operations
    before shutting down the trace provider.
    """
    if not AgentsInstrumentor._active_streaming_operations:
        return
    
    # Create a new span for each active streaming operation
    if tracer_provider:
        tracer = get_tracer(__name__, __version__, tracer_provider)
        
        for stream_id in list(AgentsInstrumentor._active_streaming_operations):
            try:
                # Create attributes for the flush span
                flush_attributes = {
                    "stream_id": str(stream_id),
                    "service.name": "agentops.agents",
                    "flush_type": "manual",
                    InstrumentationAttributes.NAME: "agentops.agents",
                    InstrumentationAttributes.VERSION: __version__,
                }
                
                # Create a new span for this streaming operation
                with tracer.start_as_current_span(
                    name=f"agents.streaming.flush.{stream_id}", 
                    kind=SpanKind.INTERNAL, 
                    attributes=flush_attributes
                ) as span:
                    # Add a marker to indicate this is a flush span
                    span.set_attribute("flush_marker", "true")
                    
                    # Force flush this span
                    if hasattr(tracer_provider, "force_flush"):
                        try:
                            tracer_provider.force_flush()
                        except Exception as e:
                            logger.warning(f"Error flushing span for streaming operation {stream_id}: {e}")
            except Exception as e:
                logger.warning(f"Error creating flush span for streaming operation {stream_id}: {e}")

