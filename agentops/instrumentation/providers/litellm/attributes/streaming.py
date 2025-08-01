"""Streaming-specific attribute extraction for LiteLLM instrumentation.

This module provides functions to extract attributes specific to
streaming operations and chunk aggregation.
"""

import time
from typing import Any, Dict, List, Optional

from agentops.instrumentation.providers.litellm.utils import safe_get_attribute


def extract_streaming_attributes(
    chunks: List[Any], start_time: float, first_chunk_time: Optional[float] = None, end_time: Optional[float] = None
) -> Dict[str, Any]:
    """Extract attributes from streaming response chunks.

    Args:
        chunks: List of streaming chunks
        start_time: When the request started
        first_chunk_time: When the first chunk arrived
        end_time: When streaming completed

    Returns:
        Dictionary of streaming attributes
    """
    attributes = {
        "llm.response.is_streaming": True,
        "llm.response.chunk_count": len(chunks),
    }

    # Timing metrics
    if end_time is None:
        end_time = time.time()

    total_duration = end_time - start_time
    attributes["llm.response.stream_duration"] = round(total_duration, 3)

    if first_chunk_time:
        attributes["llm.response.time_to_first_chunk"] = round(first_chunk_time, 3)

        # Calculate streaming rate
        if len(chunks) > 1:
            streaming_duration = total_duration - first_chunk_time
            chunks_after_first = len(chunks) - 1

            if streaming_duration > 0:
                chunks_per_second = chunks_after_first / streaming_duration
                attributes["llm.response.chunks_per_second"] = round(chunks_per_second, 2)

                # Average time between chunks
                avg_chunk_interval = streaming_duration / chunks_after_first
                attributes["llm.response.avg_chunk_interval"] = round(avg_chunk_interval, 3)

    # Analyze chunk patterns
    chunk_sizes = []
    has_content = False
    has_function_calls = False
    has_tool_calls = False
    finish_reasons = set()

    for chunk in chunks:
        # Check for content
        if hasattr(chunk, "choices") and chunk.choices:
            for choice in chunk.choices:
                # Content size
                if hasattr(choice, "delta"):
                    delta = choice.delta
                    if hasattr(delta, "content") and delta.content:
                        has_content = True
                        chunk_sizes.append(len(delta.content))

                    # Function/tool calls
                    if hasattr(delta, "function_call"):
                        has_function_calls = True
                    if hasattr(delta, "tool_calls"):
                        has_tool_calls = True

                # Finish reason
                if hasattr(choice, "finish_reason") and choice.finish_reason:
                    finish_reasons.add(choice.finish_reason)

    # Set chunk analysis attributes
    if chunk_sizes:
        attributes["llm.response.content_chunks"] = len(chunk_sizes)
        attributes["llm.response.total_streamed_content_length"] = sum(chunk_sizes)
        attributes["llm.response.avg_chunk_content_length"] = round(sum(chunk_sizes) / len(chunk_sizes), 2)
        attributes["llm.response.min_chunk_content_length"] = min(chunk_sizes)
        attributes["llm.response.max_chunk_content_length"] = max(chunk_sizes)

    attributes["llm.response.stream_has_content"] = has_content
    attributes["llm.response.stream_has_function_calls"] = has_function_calls
    attributes["llm.response.stream_has_tool_calls"] = has_tool_calls

    if finish_reasons:
        attributes["llm.response.finish_reasons"] = ",".join(finish_reasons)

    return attributes


def aggregate_streaming_chunks(chunks: List[Any]) -> Dict[str, Any]:
    """Aggregate streaming chunks into final response metrics.

    Args:
        chunks: List of streaming chunks

    Returns:
        Dictionary of aggregated metrics
    """
    aggregated = {
        "content": "",
        "function_call": None,
        "tool_calls": [],
        "finish_reason": None,
        "model": None,
        "id": None,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

    # Aggregate content and metadata
    content_parts = []
    function_call_parts = {}
    tool_calls_by_index = {}

    for chunk in chunks:
        # Model and ID (usually in first chunk)
        if hasattr(chunk, "model") and chunk.model and not aggregated["model"]:
            aggregated["model"] = chunk.model
        if hasattr(chunk, "id") and chunk.id and not aggregated["id"]:
            aggregated["id"] = chunk.id

        # Process choices
        if hasattr(chunk, "choices") and chunk.choices:
            for choice in chunk.choices:
                choice_index = getattr(choice, "index", 0)

                # Delta content
                if hasattr(choice, "delta"):
                    delta = choice.delta

                    # Text content
                    if hasattr(delta, "content") and delta.content:
                        content_parts.append(delta.content)

                    # Function call
                    if hasattr(delta, "function_call"):
                        func_call = delta.function_call

                        if choice_index not in function_call_parts:
                            function_call_parts[choice_index] = {"name": "", "arguments": ""}

                        if hasattr(func_call, "name") and func_call.name:
                            function_call_parts[choice_index]["name"] = func_call.name

                        if hasattr(func_call, "arguments") and func_call.arguments:
                            function_call_parts[choice_index]["arguments"] += func_call.arguments

                    # Tool calls
                    if hasattr(delta, "tool_calls") and delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            tool_index = getattr(tool_call, "index", 0)

                            if tool_index not in tool_calls_by_index:
                                tool_calls_by_index[tool_index] = {
                                    "id": getattr(tool_call, "id", None),
                                    "type": getattr(tool_call, "type", "function"),
                                    "function": {"name": "", "arguments": ""},
                                }

                            if hasattr(tool_call, "id") and tool_call.id:
                                tool_calls_by_index[tool_index]["id"] = tool_call.id

                            if hasattr(tool_call, "function"):
                                func = tool_call.function
                                if hasattr(func, "name") and func.name:
                                    tool_calls_by_index[tool_index]["function"]["name"] = func.name
                                if hasattr(func, "arguments") and func.arguments:
                                    tool_calls_by_index[tool_index]["function"]["arguments"] += func.arguments

                # Finish reason (usually in last chunk)
                if hasattr(choice, "finish_reason") and choice.finish_reason:
                    aggregated["finish_reason"] = choice.finish_reason

        # Usage (sometimes in chunks, sometimes only in final)
        if hasattr(chunk, "usage") and chunk.usage:
            usage = chunk.usage
            for key in ["prompt_tokens", "completion_tokens", "total_tokens"]:
                value = getattr(usage, key, None)
                if value:
                    aggregated["usage"][key] = value

    # Compile final content
    aggregated["content"] = "".join(content_parts)

    # Compile function call
    if function_call_parts:
        # Use the first choice's function call
        first_func_call = function_call_parts.get(0)
        if first_func_call and (first_func_call["name"] or first_func_call["arguments"]):
            aggregated["function_call"] = first_func_call

    # Compile tool calls
    if tool_calls_by_index:
        aggregated["tool_calls"] = list(tool_calls_by_index.values())

    return aggregated


def extract_streaming_performance_metrics(chunks: List[Any], timings: Dict[str, float]) -> Dict[str, Any]:
    """Extract performance metrics from streaming response.

    Args:
        chunks: List of streaming chunks
        timings: Dictionary with timing information

    Returns:
        Dictionary of performance metrics
    """
    metrics = {}

    # Extract chunk timestamps if available
    chunk_times = []
    for chunk in chunks:
        # Some providers include timestamps
        timestamp = safe_get_attribute(chunk, "created")
        if timestamp:
            chunk_times.append(timestamp)

    if len(chunk_times) >= 2:
        # Calculate inter-chunk delays
        delays = []
        for i in range(1, len(chunk_times)):
            delay = chunk_times[i] - chunk_times[i - 1]
            delays.append(delay)

        if delays:
            metrics["llm.streaming.avg_inter_chunk_delay"] = round(sum(delays) / len(delays), 3)
            metrics["llm.streaming.max_inter_chunk_delay"] = round(max(delays), 3)
            metrics["llm.streaming.min_inter_chunk_delay"] = round(min(delays), 3)

            # Detect potential stalls (delays > 1 second)
            stalls = [d for d in delays if d > 1.0]
            if stalls:
                metrics["llm.streaming.stall_count"] = len(stalls)
                metrics["llm.streaming.total_stall_time"] = round(sum(stalls), 3)

    # Token generation rate (if we have token counts)
    total_tokens = 0
    for chunk in chunks:
        if hasattr(chunk, "usage") and chunk.usage:
            completion_tokens = safe_get_attribute(chunk.usage, "completion_tokens")
            if completion_tokens:
                total_tokens = max(total_tokens, completion_tokens)

    if total_tokens > 0 and "stream_duration" in timings:
        duration = timings["stream_duration"]
        if duration > 0:
            tokens_per_second = total_tokens / duration
            metrics["llm.streaming.tokens_per_second"] = round(tokens_per_second, 2)

    return metrics


def detect_streaming_issues(chunks: List[Any]) -> Dict[str, Any]:
    """Detect potential issues in streaming response.

    Args:
        chunks: List of streaming chunks

    Returns:
        Dictionary of detected issues
    """
    issues = {}

    # Check for empty chunks
    empty_chunks = 0
    duplicate_chunks = 0
    seen_contents = set()

    for chunk in chunks:
        chunk_has_content = False

        if hasattr(chunk, "choices") and chunk.choices:
            for choice in chunk.choices:
                if hasattr(choice, "delta"):
                    delta = choice.delta

                    # Check for content
                    content = safe_get_attribute(delta, "content")
                    if content:
                        chunk_has_content = True

                        # Check for duplicates
                        if content in seen_contents:
                            duplicate_chunks += 1
                        else:
                            seen_contents.add(content)

        if not chunk_has_content:
            empty_chunks += 1

    if empty_chunks > 0:
        issues["llm.streaming.empty_chunks"] = empty_chunks
        issues["llm.streaming.empty_chunk_ratio"] = round(empty_chunks / len(chunks), 3)

    if duplicate_chunks > 0:
        issues["llm.streaming.duplicate_chunks"] = duplicate_chunks

    # Check for inconsistent chunk structure
    chunk_structures = set()
    for chunk in chunks:
        structure = []
        if hasattr(chunk, "id"):
            structure.append("id")
        if hasattr(chunk, "model"):
            structure.append("model")
        if hasattr(chunk, "choices"):
            structure.append("choices")
        if hasattr(chunk, "usage"):
            structure.append("usage")

        chunk_structures.add(tuple(structure))

    if len(chunk_structures) > 1:
        issues["llm.streaming.inconsistent_structure"] = True
        issues["llm.streaming.structure_variants"] = len(chunk_structures)

    return issues
