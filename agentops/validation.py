"""
AgentOps Validation Module

This module provides functions to validate that spans have been sent to AgentOps
using the public API. This is useful for testing and verification purposes.
"""

import asyncio
import os
import time
from typing import Optional, Dict, List, Any, Tuple

import requests

from agentops.exceptions import ApiServerException
from agentops.logging import logger


class ValidationError(Exception):
    """Raised when span validation fails."""

    pass


async def get_jwt_token(api_key: Optional[str] = None) -> str:
    """
    Exchange API key for JWT token asynchronously.

    Args:
        api_key: Optional API key. If not provided, uses AGENTOPS_API_KEY env var.

    Returns:
        JWT bearer token, or None if failed

    Note:
        This function never throws exceptions - all errors are handled gracefully
    """
    try:
        if api_key is None:
            from agentops import get_client

            client = get_client()
            if client and client.config.api_key:
                api_key = client.config.api_key
            else:
                api_key = os.getenv("AGENTOPS_API_KEY")
                if not api_key:
                    logger.warning("No API key provided and AGENTOPS_API_KEY environment variable not set")
                    return None

        # Use a separate aiohttp session for validation to avoid conflicts
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.agentops.ai/public/v1/auth/access_token",
                json={"api_key": api_key},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status >= 400:
                    logger.warning(f"Failed to get JWT token: HTTP {response.status} - backend may be unavailable")
                    return None

                response_data = await response.json()

                if "bearer" not in response_data:
                    logger.warning("Failed to get JWT token: No bearer token in response")
                    return None

                return response_data["bearer"]

    except Exception as e:
        logger.warning(f"Failed to get JWT token: {e} - continuing without authentication")
        return None


def get_jwt_token_sync(api_key: Optional[str] = None) -> Optional[str]:
    """
    Synchronous wrapper for get_jwt_token - runs async function in event loop.

    Args:
        api_key: Optional API key. If not provided, uses AGENTOPS_API_KEY env var.

    Returns:
        JWT bearer token, or None if failed

    Note:
        This function never throws exceptions - all errors are handled gracefully
    """
    try:
        import concurrent.futures

        # Always run in a separate thread to avoid event loop issues
        def run_in_thread():
            return asyncio.run(get_jwt_token(api_key))

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
    except Exception as e:
        logger.warning(f"Failed to get JWT token synchronously: {e}")
        return None


def get_trace_details(trace_id: str, jwt_token: str) -> Dict[str, Any]:
    """
    Get trace details from AgentOps API.

    Args:
        trace_id: The trace ID to query
        jwt_token: JWT authentication token

    Returns:
        Trace details including spans

    Raises:
        ApiServerException: If API request fails
    """
    try:
        response = requests.get(
            f"https://api.agentops.ai/public/v1/traces/{trace_id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise ApiServerException(f"Failed to get trace details: {e}")


def get_trace_metrics(trace_id: str, jwt_token: str) -> Dict[str, Any]:
    """
    Get trace metrics from AgentOps API.

    Args:
        trace_id: The trace ID to query
        jwt_token: JWT authentication token

    Returns:
        Trace metrics including token counts and costs

    Raises:
        ApiServerException: If API request fails
    """
    try:
        response = requests.get(
            f"https://api.agentops.ai/public/v1/traces/{trace_id}/metrics",
            headers={"Authorization": f"Bearer {jwt_token}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise ApiServerException(f"Failed to get trace metrics: {e}")


def check_llm_spans(spans: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    Check if any LLM spans are present in the trace.

    Args:
        spans: List of span dictionaries

    Returns:
        Tuple of (has_llm_spans, llm_span_names)
    """
    llm_spans = []

    for span in spans:
        span_name = span.get("span_name", "unnamed_span")
        span_attributes = span.get("span_attributes", {})
        is_llm_span = False

        if span_attributes:
            # Check for LLM span kind - handle both flat and nested structures
            span_kind = span_attributes.get("agentops.span.kind", "")
            if not span_kind:
                # Check nested structure: agentops.span.kind or agentops -> span -> kind
                agentops_attrs = span_attributes.get("agentops", {})
                if isinstance(agentops_attrs, dict):
                    span_attrs = agentops_attrs.get("span", {})
                    if isinstance(span_attrs, dict):
                        span_kind = span_attrs.get("kind", "")

            is_llm_span = span_kind == "llm"

            # Alternative check: Look for gen_ai attributes
            if not is_llm_span:
                gen_ai_attrs = span_attributes.get("gen_ai", {})
                if isinstance(gen_ai_attrs, dict):
                    if "prompt" in gen_ai_attrs or "completion" in gen_ai_attrs:
                        is_llm_span = True

            # Check for LLM request type
            if not is_llm_span:
                llm_request_type = span_attributes.get("gen_ai.request.type", "")
                if not llm_request_type:
                    # Also check for older llm.request.type format
                    llm_request_type = span_attributes.get("llm.request.type", "")
                if llm_request_type in ["chat", "completion"]:
                    is_llm_span = True

        if is_llm_span:
            llm_spans.append(span_name)

    return len(llm_spans) > 0, llm_spans


def validate_trace_spans(
    trace_id: Optional[str] = None,
    trace_context: Optional[Any] = None,
    max_retries: int = 10,
    retry_delay: float = 1.0,
    check_llm: bool = True,
    min_spans: int = 1,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate that spans have been sent to AgentOps.

    Args:
        trace_id: Direct trace ID to validate
        trace_context: TraceContext object from start_trace (alternative to trace_id)
        max_retries: Maximum number of retries to wait for spans to appear
        retry_delay: Delay between retries in seconds
        check_llm: Whether to specifically check for LLM spans
        min_spans: Minimum number of spans expected
        api_key: Optional API key (uses environment variable if not provided)

    Returns:
        Dictionary containing validation results and metrics

    Raises:
        ValidationError: If validation fails
        ValueError: If neither trace_id nor trace_context is provided
    """
    # Extract trace ID
    if trace_id is None and trace_context is None:
        # Try to get from current span
        try:
            from opentelemetry.trace import get_current_span

            current_span = get_current_span()
            if current_span and hasattr(current_span, "get_span_context"):
                span_context = current_span.get_span_context()
                if hasattr(span_context, "trace_id") and span_context.trace_id:
                    if isinstance(span_context.trace_id, int):
                        trace_id = format(span_context.trace_id, "032x")
                    else:
                        trace_id = str(span_context.trace_id)
        except ImportError:
            pass

    elif trace_context is not None and trace_id is None:
        # Extract from TraceContext
        if hasattr(trace_context, "span") and trace_context.span:
            span_context = trace_context.span.get_span_context()
            if hasattr(span_context, "trace_id"):
                if isinstance(span_context.trace_id, int):
                    trace_id = format(span_context.trace_id, "032x")
                else:
                    trace_id = str(span_context.trace_id)

    if trace_id is None:
        raise ValueError("No trace ID found. Provide either trace_id or trace_context parameter.")

    # Get JWT token
    jwt_token = get_jwt_token_sync(api_key)
    if not jwt_token:
        logger.warning("Could not obtain JWT token - validation will be skipped")
        return {
            "trace_id": trace_id,
            "span_count": 0,
            "spans": [],
            "has_llm_spans": False,
            "llm_span_names": [],
            "metrics": None,
            "validation_skipped": True,
            "reason": "No JWT token available",
        }

    logger.info(f"Validating spans for trace ID: {trace_id}")

    for attempt in range(max_retries):
        try:
            # Get trace details
            trace_details = get_trace_details(trace_id, jwt_token)
            spans = trace_details.get("spans", [])

            if len(spans) >= min_spans:
                logger.info(f"Found {len(spans)} span(s) in trace")

                # Prepare result
                result = {
                    "trace_id": trace_id,
                    "span_count": len(spans),
                    "spans": spans,
                    "has_llm_spans": False,
                    "llm_span_names": [],
                    "metrics": None,
                }

                # Get metrics first - if we have token usage, we definitely have LLM spans
                try:
                    metrics = get_trace_metrics(trace_id, jwt_token)
                    result["metrics"] = metrics

                    if metrics:
                        logger.info(
                            f"Trace metrics - Total tokens: {metrics.get('total_tokens', 0)}, "
                            f"Cost: ${metrics.get('total_cost', '0.0000')}"
                        )

                        # If we have token usage > 0, we definitely have LLM activity
                        if metrics.get("total_tokens", 0) > 0:
                            result["has_llm_spans"] = True
                            logger.info("LLM activity confirmed via token usage metrics")
                except Exception as e:
                    logger.warning(f"Could not retrieve metrics: {e}")

                # Check for LLM spans if requested and not already confirmed via metrics
                if check_llm and not result["has_llm_spans"]:
                    has_llm_spans, llm_span_names = check_llm_spans(spans)
                    result["has_llm_spans"] = has_llm_spans
                    result["llm_span_names"] = llm_span_names

                    if has_llm_spans:
                        logger.info(f"Found LLM spans: {', '.join(llm_span_names)}")
                    else:
                        logger.warning("No LLM spans found via attribute inspection")

                # Final validation
                if check_llm and not result["has_llm_spans"]:
                    raise ValidationError(
                        f"No LLM activity detected in trace {trace_id}. "
                        f"Found spans: {[s.get('span_name', 'unnamed') for s in spans]}, "
                        f"Token usage: {result.get('metrics', {}).get('total_tokens', 0)}"
                    )

                return result

            else:
                logger.debug(
                    f"Only {len(spans)} spans found, expected at least {min_spans}. "
                    f"Retrying... ({attempt + 1}/{max_retries})"
                )

        except ApiServerException as e:
            logger.debug(f"API error during validation: {e}. Retrying... ({attempt + 1}/{max_retries})")

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    raise ValidationError(
        f"Validation failed for trace {trace_id} after {max_retries} attempts. "
        f"Expected at least {min_spans} spans"
        + (", including LLM activity" if check_llm else "")
        + ". Please check that tracking is properly configured."
    )


def print_validation_summary(result: Dict[str, Any]) -> None:
    """
    Print a user-friendly summary of validation results.

    Args:
        result: Validation result dictionary from validate_trace_spans
    """
    print("\n" + "=" * 50)
    print("🔍 AgentOps Span Validation Results")
    print("=" * 50)

    if result.get("validation_skipped"):
        print(f"⚠️  Validation skipped: {result.get('reason', 'Unknown reason')}")
        return

    print(f"✅ Found {result['span_count']} span(s) in trace")

    if result.get("has_llm_spans"):
        if result.get("llm_span_names"):
            print(f"✅ Found LLM spans: {', '.join(result['llm_span_names'])}")
        else:
            # LLM activity confirmed via metrics
            print("✅ LLM activity confirmed via token usage metrics")
    elif "has_llm_spans" in result:
        print("⚠️  No LLM activity detected")

    if result.get("metrics"):
        metrics = result["metrics"]
        print("\n📊 Trace Metrics:")
        print(f"   - Total tokens: {metrics.get('total_tokens', 0)}")
        print(f"   - Prompt tokens: {metrics.get('prompt_tokens', 0)}")
        print(f"   - Completion tokens: {metrics.get('completion_tokens', 0)}")
        print(f"   - Total cost: ${metrics.get('total_cost', '0.0000')}")

    print("\n✅ Validation successful!")
