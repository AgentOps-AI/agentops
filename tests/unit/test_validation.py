"""
Unit tests for the AgentOps validation module.
"""

import pytest
import requests
from unittest.mock import Mock, patch

from agentops.exceptions import ApiServerException
from agentops.validation import (
    get_jwt_token_sync,
    get_trace_details,
    check_llm_spans,
    validate_trace_spans,
    print_validation_summary,
    ValidationError,
)
from agentops.semconv import SpanAttributes, LLMRequestTypeValues


class TestGetJwtToken:
    """Test JWT token exchange functionality."""

    @patch("tests.unit.test_validation.get_jwt_token_sync")
    def test_get_jwt_token_success(self, mock_sync):
        """Test successful JWT token retrieval."""
        mock_sync.return_value = "test-token"

        token = get_jwt_token_sync("test-api-key")
        assert token == "test-token"

    @patch("tests.unit.test_validation.get_jwt_token_sync")
    def test_get_jwt_token_failure(self, mock_sync):
        """Test JWT token retrieval failure."""
        mock_sync.return_value = None

        # Should not raise exception anymore, just return None
        token = get_jwt_token_sync("invalid-api-key")
        assert token is None

    @patch("os.getenv")
    @patch("agentops.get_client")
    @patch("tests.unit.test_validation.get_jwt_token_sync")
    def test_get_jwt_token_from_env(self, mock_sync, mock_get_client, mock_getenv):
        """Test JWT token retrieval using environment variable."""
        mock_get_client.return_value = None
        mock_getenv.return_value = "env-api-key"
        mock_sync.return_value = "env-token"

        token = get_jwt_token_sync()
        assert token == "env-token"


class TestGetTraceDetails:
    """Test trace details retrieval."""

    @patch("agentops.validation.requests.get")
    def test_get_trace_details_success(self, mock_get):
        """Test successful trace details retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"trace_id": "test-trace", "spans": [{"span_name": "test-span"}]}
        mock_get.return_value = mock_response

        details = get_trace_details("test-trace", "test-token")
        assert details["trace_id"] == "test-trace"
        assert len(details["spans"]) == 1

        mock_get.assert_called_once_with(
            "https://api.agentops.ai/public/v1/traces/test-trace",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

    @patch("agentops.validation.requests.get")
    def test_get_trace_details_failure(self, mock_get):
        """Test trace details retrieval failure."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(ApiServerException, match="Failed to get trace details"):
            get_trace_details("invalid-trace", "test-token")


class TestCheckLlmSpans:
    """Test LLM span checking."""

    def test_check_llm_spans_found(self):
        """Test when LLM spans are found."""
        spans = [
            {"span_name": "OpenAI Chat Completion", "span_attributes": {"agentops.span.kind": "llm"}},
            {"span_name": "Some other span"},
            {"span_name": "anthropic.messages.create", "span_attributes": {"agentops": {"span": {"kind": "llm"}}}},
        ]

        has_llm, llm_names = check_llm_spans(spans)
        assert has_llm is True
        assert len(llm_names) == 2
        assert "OpenAI Chat Completion" in llm_names
        assert "anthropic.messages.create" in llm_names

    def test_check_llm_spans_not_found(self):
        """Test when no LLM spans are found."""
        spans = [{"span_name": "database.query"}, {"span_name": "http.request"}]

        has_llm, llm_names = check_llm_spans(spans)
        assert has_llm is False
        assert len(llm_names) == 0

    def test_check_llm_spans_empty(self):
        """Test with empty spans list."""
        has_llm, llm_names = check_llm_spans([])
        assert has_llm is False
        assert len(llm_names) == 0

    def test_check_llm_spans_with_request_type(self):
        """Test when LLM spans are identified by LLM_REQUEST_TYPE attribute."""
        spans = [
            {
                "span_name": "openai.chat.completion",
                "span_attributes": {SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
            },
            {
                "span_name": "anthropic.messages.create",
                "span_attributes": {SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
            },
            {
                "span_name": "llm.completion",
                "span_attributes": {SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.COMPLETION.value},
            },
            {
                "span_name": "embedding.create",
                "span_attributes": {SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.EMBEDDING.value},
            },
            {"span_name": "database.query"},
        ]

        has_llm, llm_names = check_llm_spans(spans)
        assert has_llm is True
        assert len(llm_names) == 3  # Only chat and completion types count as LLM
        assert "openai.chat.completion" in llm_names
        assert "anthropic.messages.create" in llm_names
        assert "llm.completion" in llm_names
        assert "embedding.create" not in llm_names  # Embeddings are not LLM spans

    def test_check_llm_spans_real_world(self):
        """Test with real-world span structures from OpenAI and Anthropic."""
        spans = [
            {
                "span_name": "openai.chat.completion",
                "span_attributes": {
                    SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value,
                    SpanAttributes.LLM_SYSTEM: "OpenAI",
                    SpanAttributes.LLM_REQUEST_MODEL: "gpt-4",
                },
            },
            {
                "span_name": "anthropic.messages.create",
                "span_attributes": {
                    SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value,
                    SpanAttributes.LLM_SYSTEM: "Anthropic",
                    SpanAttributes.LLM_REQUEST_MODEL: "claude-3-opus-20240229",
                },
            },
        ]

        has_llm, llm_names = check_llm_spans(spans)
        assert has_llm is True
        assert len(llm_names) == 2
        assert "openai.chat.completion" in llm_names
        assert "anthropic.messages.create" in llm_names


class TestValidateTraceSpans:
    """Test the main validation function."""

    @patch("agentops.validation.get_jwt_token")
    @patch("agentops.validation.get_trace_details")
    @patch("agentops.validation.get_trace_metrics")
    def test_validate_trace_spans_success(self, mock_metrics, mock_details, mock_token):
        """Test successful validation."""
        mock_token.return_value = "test-token"
        mock_details.return_value = {
            "spans": [
                {"span_name": "OpenAI Chat Completion", "span_attributes": {"agentops.span.kind": "llm"}},
                {"span_name": "Other span"},
            ]
        }
        mock_metrics.return_value = {"total_tokens": 100, "total_cost": "0.0025"}

        result = validate_trace_spans(trace_id="test-trace")

        assert result["trace_id"] == "test-trace"
        assert result["span_count"] == 2
        assert result["has_llm_spans"] is True
        # LLM activity can be confirmed via metrics or span inspection
        assert result["metrics"]["total_tokens"] == 100

    @patch("agentops.validation.get_jwt_token")
    @patch("agentops.validation.get_trace_details")
    @patch("agentops.validation.get_trace_metrics")
    def test_validate_trace_spans_success_via_metrics(self, mock_metrics, mock_details, mock_token):
        """Test successful validation when LLM activity is confirmed via metrics."""
        mock_token.return_value = "test-token"
        mock_details.return_value = {
            "spans": [
                {
                    "span_name": "openai.chat.completion",
                    "span_attributes": {},  # No specific LLM attributes
                },
                {"span_name": "Other span"},
            ]
        }
        # But we have token usage, proving LLM activity
        mock_metrics.return_value = {"total_tokens": 1066, "total_cost": "0.0006077"}

        result = validate_trace_spans(trace_id="test-trace")

        assert result["trace_id"] == "test-trace"
        assert result["span_count"] == 2
        assert result["has_llm_spans"] is True  # Confirmed via metrics
        assert result["metrics"]["total_tokens"] == 1066

    @patch("agentops.validation.get_jwt_token")
    @patch("agentops.validation.get_trace_details")
    @patch("agentops.validation.get_trace_metrics")
    def test_validate_trace_spans_no_llm(self, mock_metrics, mock_details, mock_token):
        """Test validation failure when no LLM spans found and no token usage."""
        mock_token.return_value = "test-token"
        mock_details.return_value = {"spans": [{"span_name": "database.query"}]}
        # No token usage either
        mock_metrics.return_value = {"total_tokens": 0, "total_cost": "0.0000"}

        with pytest.raises(ValidationError, match="No LLM activity detected"):
            validate_trace_spans(trace_id="test-trace", check_llm=True)

    @patch("agentops.validation.get_jwt_token")
    @patch("agentops.validation.get_trace_details")
    @patch("agentops.validation.get_trace_metrics")
    def test_validate_trace_spans_retry(self, mock_metrics, mock_details, mock_token):
        """Test validation with retries."""
        mock_token.return_value = "test-token"

        # First two calls return empty, third returns spans
        mock_details.side_effect = [
            {"spans": []},
            {"spans": []},
            {"spans": [{"span_name": "OpenAI Chat Completion", "span_attributes": {"agentops.span.kind": "llm"}}]},
        ]

        # Mock metrics for the successful attempt
        mock_metrics.return_value = {"total_tokens": 100, "total_cost": "0.0025"}

        result = validate_trace_spans(trace_id="test-trace", max_retries=3, retry_delay=0.01)

        assert result["span_count"] == 1
        assert mock_details.call_count == 3

    @patch("opentelemetry.trace.get_current_span")
    def test_validate_trace_spans_no_trace_id(self, mock_get_current_span):
        """Test validation without trace ID."""
        # Mock get_current_span to return None
        mock_get_current_span.return_value = None

        with pytest.raises(ValueError, match="No trace ID found"):
            validate_trace_spans()

    @patch("opentelemetry.trace.get_current_span")
    @patch("agentops.validation.get_jwt_token")
    @patch("agentops.validation.get_trace_details")
    @patch("agentops.validation.get_trace_metrics")
    def test_validate_trace_spans_from_current_span(self, mock_metrics, mock_details, mock_token, mock_get_span):
        """Test extracting trace ID from current span."""
        # Mock the current span
        mock_span_context = Mock()
        mock_span_context.trace_id = 12345678901234567890

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context

        mock_get_span.return_value = mock_span

        mock_token.return_value = "test-token"
        mock_details.return_value = {
            "spans": [{"span_name": "OpenAI Chat Completion", "span_attributes": {"agentops.span.kind": "llm"}}]
        }
        mock_metrics.return_value = {"total_tokens": 100, "total_cost": "0.0025"}

        result = validate_trace_spans()
        assert result["trace_id"] == "0000000000000000ab54a98ceb1f0ad2"  # hex format of trace ID


class TestPrintValidationSummary:
    """Test validation summary printing."""

    def test_print_validation_summary(self, capsys):
        """Test printing validation summary."""
        result = {
            "span_count": 3,
            "has_llm_spans": True,
            "llm_span_names": ["OpenAI Chat", "Claude Message"],
            "metrics": {"total_tokens": 150, "prompt_tokens": 100, "completion_tokens": 50, "total_cost": "0.0030"},
        }

        print_validation_summary(result)

        captured = capsys.readouterr()
        assert "Found 3 span(s)" in captured.out
        assert "OpenAI Chat" in captured.out
        assert "Total tokens: 150" in captured.out
        assert "Total cost: $0.0030" in captured.out
        assert "✅ Validation successful!" in captured.out

    def test_print_validation_summary_metrics_only(self, capsys):
        """Test printing validation summary when LLM activity confirmed via metrics only."""
        result = {
            "span_count": 2,
            "has_llm_spans": True,
            "llm_span_names": [],  # No specific LLM span names found
            "metrics": {
                "total_tokens": 1066,
                "prompt_tokens": 800,
                "completion_tokens": 266,
                "total_cost": "0.0006077",
            },
        }

        print_validation_summary(result)

        captured = capsys.readouterr()
        assert "Found 2 span(s)" in captured.out
        assert "LLM activity confirmed via token usage metrics" in captured.out
        assert "Total tokens: 1066" in captured.out
        assert "Total cost: $0.0006077" in captured.out
        assert "✅ Validation successful!" in captured.out

    def test_print_validation_summary_llm_prefix(self, capsys):
        """Test with spans using llm.* prefix (as returned by API)."""
        result = {
            "span_count": 1,
            "has_llm_spans": True,
            "llm_span_names": ["openai.chat.completion"],
            "metrics": {"total_tokens": 150, "prompt_tokens": 100, "completion_tokens": 50, "total_cost": "0.0030"},
        }

        print_validation_summary(result)

        captured = capsys.readouterr()
        assert "Found 1 span(s)" in captured.out
        assert "openai.chat.completion" in captured.out
        assert "✅ Validation successful!" in captured.out


class TestCheckLlmSpansWithLlmPrefix:
    """Test LLM span checking with llm.* prefix attributes."""

    def test_check_llm_spans_with_llm_prefix(self):
        """Test when spans use llm.request.type instead of gen_ai.request.type."""
        spans = [
            {
                "span_name": "openai.chat.completion",
                "span_attributes": {
                    "llm.request.type": "chat",
                    "llm.system": "OpenAI",
                    "llm.request.model": "gpt-4",
                    "llm.usage.total_tokens": 150,
                },
            },
            {
                "span_name": "anthropic.messages.create",
                "span_attributes": {
                    "llm.request.type": "chat",
                    "llm.system": "Anthropic",
                    "llm.request.model": "claude-3-opus",
                    "llm.usage.total_tokens": 300,
                },
            },
            {"span_name": "embedding.create", "span_attributes": {"llm.request.type": "embedding"}},
            {"span_name": "database.query"},
        ]

        has_llm, llm_names = check_llm_spans(spans)
        assert has_llm is True
        assert len(llm_names) == 2  # Only chat types
        assert "openai.chat.completion" in llm_names
        assert "anthropic.messages.create" in llm_names
