"""Metrics utilities for the OpenAI Agents instrumentation.

This module contains functions for recording token usage metrics from OpenAI responses.
"""
from typing import Any, Dict

from agentops.semconv import SpanAttributes
from agentops.instrumentation.openai_agents.tokens import process_token_usage, map_token_type_to_metric_name


def record_token_usage(histogram, usage: Dict[str, Any], model_name: str) -> None:
    """Record token usage metrics from usage data.
    
    Args:
        histogram: OpenTelemetry histogram instrument for recording token usage
        usage: Dictionary containing token usage data
        model_name: Name of the model used
    """
    if histogram is None:
        return
        
    # Process all token types using our standardized processor
    token_counts = process_token_usage(usage, {})
    
    # Common attributes for all metrics
    common_attributes = {
        "model": model_name,
        SpanAttributes.LLM_REQUEST_MODEL: model_name,
        SpanAttributes.LLM_SYSTEM: "openai",
    }
    
    # Record metrics for each token type
    for token_type, count in token_counts.items():
        # Skip recording if no count
        if not count:
            continue
            
        # Map token type to simplified metric name
        metric_token_type = map_token_type_to_metric_name(token_type)
        
        # Record the metric
        histogram.record(
            count,
            {
                "token_type": metric_token_type,
                **common_attributes,
            },
        )