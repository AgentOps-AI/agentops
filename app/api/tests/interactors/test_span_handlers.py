from unittest.mock import patch

import pytest
from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_RESPONSE_MODEL,
    GEN_AI_SYSTEM,
    GenAiOperationNameValues,
)

from agentops.api.encoders.spans import SpanAttributeEncoder
from agentops.api.interactors.spans import (
    GEN_AI_TOOL_CALL_ID,
    GEN_AI_TOOL_NAME,
    LEGACY_EMBEDDING,
    LEGACY_LLM,
    LEGACY_SYSTEM,
    LOG_MESSAGE,
    LOG_SEVERITY,
    AgentopsGenAISpanSubtype,
    AgentopsSpanType,
    classify_gen_ai_span_subtype,
    classify_span,
    handle_gen_ai_span,
)


@pytest.mark.asyncio
async def test_classify_span_gen_ai():
    """Test that Gen AI spans are correctly classified."""
    # Test with legacy ai.system attribute
    span = {"attributes": {LEGACY_SYSTEM: "openai"}}
    assert await classify_span(span) == AgentopsSpanType.GEN_AI

    # Test with legacy ai.llm attribute
    span = {"attributes": {LEGACY_LLM: "gpt-4"}}
    assert await classify_span(span) == AgentopsSpanType.GEN_AI

    # Test with legacy ai.embedding attribute
    span = {"attributes": {LEGACY_EMBEDDING: "text-embedding-ada-002"}}
    assert await classify_span(span) == AgentopsSpanType.GEN_AI

    # Test with gen_ai.system attribute
    span = {"attributes": {GEN_AI_SYSTEM: "openai"}}
    assert await classify_span(span) == AgentopsSpanType.GEN_AI

    # Test with gen_ai.operation.name attribute
    span = {"attributes": {GEN_AI_OPERATION_NAME: "chat"}}
    assert await classify_span(span) == AgentopsSpanType.GEN_AI

    # Test with gen_ai.request.model attribute
    span = {"attributes": {GEN_AI_REQUEST_MODEL: "gpt-4"}}
    assert await classify_span(span) == AgentopsSpanType.GEN_AI

    # Test with gen_ai.response.model attribute
    span = {"attributes": {GEN_AI_RESPONSE_MODEL: "gpt-4"}}
    assert await classify_span(span) == AgentopsSpanType.GEN_AI


@pytest.mark.asyncio
async def test_classify_span_log():
    """Test that log spans are correctly classified."""
    # Test with log.severity attribute
    span = {"attributes": {LOG_SEVERITY: "INFO"}}
    assert await classify_span(span) == AgentopsSpanType.LOG

    # Test with log.message attribute
    span = {"attributes": {LOG_MESSAGE: "Test message"}}
    assert await classify_span(span) == AgentopsSpanType.LOG


@pytest.mark.asyncio
async def test_classify_span_session_update():
    """Test that session update spans are correctly classified."""
    # Test with no relevant attributes
    span = {"attributes": {"other": "value"}}
    assert await classify_span(span) == AgentopsSpanType.SESSION_UPDATE


@pytest.mark.asyncio
async def test_classify_gen_ai_span_subtype():
    """Test that Gen AI span subtypes are correctly classified."""
    # Test tool span
    span = {"attributes": {GEN_AI_TOOL_NAME: "calculator"}}
    assert await classify_gen_ai_span_subtype(span) == AgentopsGenAISpanSubtype.TOOL

    span = {"attributes": {GEN_AI_TOOL_CALL_ID: "call_123"}}
    assert await classify_gen_ai_span_subtype(span) == AgentopsGenAISpanSubtype.TOOL

    # Test chat span
    span = {"attributes": {GEN_AI_OPERATION_NAME: GenAiOperationNameValues.CHAT.value}}
    assert await classify_gen_ai_span_subtype(span) == AgentopsGenAISpanSubtype.CHAT

    # Test completion span
    span = {"attributes": {GEN_AI_OPERATION_NAME: GenAiOperationNameValues.TEXT_COMPLETION.value}}
    assert await classify_gen_ai_span_subtype(span) == AgentopsGenAISpanSubtype.COMPLETION

    # Test embedding span
    span = {"attributes": {GEN_AI_OPERATION_NAME: GenAiOperationNameValues.EMBEDDINGS.value}}
    assert await classify_gen_ai_span_subtype(span) == AgentopsGenAISpanSubtype.EMBEDDING

    span = {"attributes": {LEGACY_EMBEDDING: "text-embedding-ada-002"}}
    assert await classify_gen_ai_span_subtype(span) == AgentopsGenAISpanSubtype.EMBEDDING

    # Test default
    span = {"attributes": {GEN_AI_SYSTEM: "openai"}}
    assert await classify_gen_ai_span_subtype(span) == AgentopsGenAISpanSubtype.GENERIC


@pytest.mark.asyncio
async def test_handle_gen_ai_span():
    """Test that Gen AI spans are correctly handled."""
    session_id = "test-session"
    span = {
        "agent_id": "test-agent",
        "trace_id": "test-trace",
        "span_id": "test-span",
        "parent_span_id": "test-parent",
        "name": "test-span",
        "kind": "client",
        "start_time": "2023-01-01T00:00:00Z",
        "end_time": "2023-01-01T00:00:01Z",
        "attributes": {
            GEN_AI_SYSTEM: "openai",
            GEN_AI_OPERATION_NAME: GenAiOperationNameValues.CHAT.value,
            GEN_AI_REQUEST_MODEL: "gpt-4",
        },
    }

    # Mock the SpanAttributeEncoder.encode method
    with patch.object(SpanAttributeEncoder, 'encode', return_value=b"encoded"):
        span_data = await handle_gen_ai_span(span, session_id)

    assert span_data["session_id"] == session_id
    assert span_data["agent_id"] == span["agent_id"]
    assert span_data["trace_id"] == span["trace_id"]
    assert span_data["span_id"] == span["span_id"]
    assert span_data["parent_span_id"] == span["parent_span_id"]
    assert span_data["name"] == span["name"]
    assert span_data["kind"] == span["kind"]
    assert span_data["start_time"] == span["start_time"]
    assert span_data["end_time"] == span["end_time"]
    assert span_data["attributes"] == b"encoded"
    assert span_data["span_type"] == AgentopsSpanType.GEN_AI
    assert span_data["span_subtype"] == AgentopsGenAISpanSubtype.CHAT
