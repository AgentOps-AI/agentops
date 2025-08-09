from enum import Enum
from typing import Any, Dict

from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_RESPONSE_MODEL,
    GEN_AI_SYSTEM,
    GenAiOperationNameValues,
)
from opentelemetry.semconv_ai import LLMRequestTypeValues, SpanAttributes
from opentelemetry.trace import SpanKind

from agentops.api.encoders.spans import SpanAttributeEncoder


# ==========================================
# Internal Span Classifications
# ==========================================
class AgentopsSpanType(str, Enum):
    """Internal classification of span types for AgentOps processing."""

    SESSION_UPDATE = "session_update"
    GEN_AI = "gen_ai"
    LOG = "log"


class AgentopsGenAISpanSubtype(str, Enum):
    """Internal classification of GenAI span subtypes for AgentOps processing.

    Note: These are NOT OpenTelemetry standard span types, but rather
    internal classifications used by AgentOps for processing."""

    CHAT = "gen_ai_chat"
    COMPLETION = "gen_ai_completion"
    TOOL = "gen_ai_tool"
    EMBEDDING = "gen_ai_embedding"
    GENERIC = "gen_ai"  # Generic/fallback type


# Legacy/alternative attributes (used in some implementations)
LEGACY_SYSTEM = "ai.system"
LEGACY_LLM = "ai.llm"
LEGACY_EMBEDDING = "ai.embedding"

# Tool attributes - these aren't yet in the standard, so we define them here
GEN_AI_TOOL_NAME = "gen_ai.tool.name"
GEN_AI_TOOL_CALL_ID = "gen_ai.tool.call.id"

# Log attributes
LOG_SEVERITY = "log.severity"
LOG_MESSAGE = "log.message"


async def classify_span(span: Dict[str, Any]) -> str:
    """Classify a span based on semantic conventions."""
    # Get span attributes
    attributes = span.get("attributes", {})

    # Check for Gen AI spans using multiple criteria
    if (
        LEGACY_SYSTEM in attributes
        or LEGACY_LLM in attributes
        or LEGACY_EMBEDDING in attributes
        or GEN_AI_SYSTEM in attributes
        or GEN_AI_OPERATION_NAME in attributes
        or GEN_AI_REQUEST_MODEL in attributes
        or GEN_AI_RESPONSE_MODEL in attributes
        or SpanAttributes.LLM_REQUEST_MODEL in attributes
        or SpanAttributes.LLM_RESPONSE_MODEL in attributes
        or SpanAttributes.LLM_SYSTEM in attributes
    ):
        return AgentopsSpanType.GEN_AI

    # Check for Log spans
    if LOG_SEVERITY in attributes or LOG_MESSAGE in attributes:
        return AgentopsSpanType.LOG

    # Default to Session Update span
    return AgentopsSpanType.SESSION_UPDATE


async def classify_gen_ai_span_subtype(span: Dict[str, Any]) -> str:
    """Further classify a Gen AI span into subtypes based on attributes."""
    attributes = span.get("attributes", {})

    # Check for tool usage
    if GEN_AI_TOOL_NAME in attributes or GEN_AI_TOOL_CALL_ID in attributes:
        return AgentopsGenAISpanSubtype.TOOL

    # Check for operation type
    operation_name = attributes.get(GEN_AI_OPERATION_NAME)
    if operation_name:
        if operation_name == GenAiOperationNameValues.CHAT.value:
            return AgentopsGenAISpanSubtype.CHAT
        elif operation_name == GenAiOperationNameValues.TEXT_COMPLETION.value:
            return AgentopsGenAISpanSubtype.COMPLETION
        elif operation_name == GenAiOperationNameValues.EMBEDDINGS.value:
            return AgentopsGenAISpanSubtype.EMBEDDING

    # Check for request type from LLMRequestTypeValues
    request_type = attributes.get(SpanAttributes.LLM_REQUEST_TYPE)
    if request_type:
        if request_type == LLMRequestTypeValues.CHAT.value:
            return AgentopsGenAISpanSubtype.CHAT
        elif request_type == LLMRequestTypeValues.COMPLETION.value:
            return AgentopsGenAISpanSubtype.COMPLETION
        elif request_type == LLMRequestTypeValues.EMBEDDING.value:
            return AgentopsGenAISpanSubtype.EMBEDDING

    # Check for embedding-specific attributes
    if LEGACY_EMBEDDING in attributes:
        return AgentopsGenAISpanSubtype.EMBEDDING

    # Default to general Gen AI span
    return AgentopsGenAISpanSubtype.GENERIC


async def handle_session_update_span(span: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Handle a session update span."""
    # Extract span data
    span_data = {
        "session_id": session_id,
        "agent_id": span.get("agent_id"),
        "trace_id": span.get("trace_id"),
        "span_id": span.get("span_id"),
        "parent_span_id": span.get("parent_span_id"),
        "name": span.get("name"),
        "kind": span.get("kind", SpanKind.INTERNAL),
        "start_time": span.get("start_time"),
        "end_time": span.get("end_time"),
        "attributes": SpanAttributeEncoder.encode(span.get("attributes", {})),
        "span_type": AgentopsSpanType.SESSION_UPDATE,
    }
    return span_data


async def handle_gen_ai_span(span: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Handle a Gen AI span."""
    # Get the Gen AI span subtype
    gen_ai_subtype = await classify_gen_ai_span_subtype(span)

    # Extract span data
    span_data = {
        "session_id": session_id,
        "agent_id": span.get("agent_id"),
        "trace_id": span.get("trace_id"),
        "span_id": span.get("span_id"),
        "parent_span_id": span.get("parent_span_id"),
        "name": span.get("name"),
        "kind": span.get("kind", SpanKind.CLIENT),
        "start_time": span.get("start_time"),
        "end_time": span.get("end_time"),
        "attributes": SpanAttributeEncoder.encode(span.get("attributes", {})),
        "span_type": AgentopsSpanType.GEN_AI,
        "span_subtype": gen_ai_subtype,
    }
    return span_data


async def handle_log_span(span: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Handle a log span."""
    # Extract span data
    span_data = {
        "session_id": session_id,
        "agent_id": span.get("agent_id"),
        "trace_id": span.get("trace_id"),
        "span_id": span.get("span_id"),
        "parent_span_id": span.get("parent_span_id"),
        "name": span.get("name"),
        "kind": span.get("kind", SpanKind.INTERNAL),
        "start_time": span.get("start_time"),
        "end_time": span.get("end_time"),
        "attributes": SpanAttributeEncoder.encode(span.get("attributes", {})),
        "span_type": AgentopsSpanType.LOG,
    }
    return span_data
