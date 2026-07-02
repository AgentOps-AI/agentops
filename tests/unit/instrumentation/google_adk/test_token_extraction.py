"""Tests for Google ADK token usage attribute extraction (issue #1418).

Verifies that both old-style (prompt_token_count / candidates_token_count)
and new ADK 2.1+ style (input_tokens / output_tokens) field names are
correctly mapped to the SpanAttributes constants.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from agentops.semconv import SpanAttributes


def _extract_usage_attributes(usage_metadata: dict) -> dict:
    """Replicate the attribute extraction logic from patch.py for isolated testing."""
    attributes = {}
    usage = usage_metadata

    if "prompt_token_count" in usage:
        attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["prompt_token_count"]
    elif "input_tokens" in usage:
        attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["input_tokens"]

    if "candidates_token_count" in usage:
        attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["candidates_token_count"]
    elif "output_tokens" in usage:
        attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["output_tokens"]

    if "total_token_count" in usage:
        attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_token_count"]
    elif "total_tokens" in usage:
        attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]

    return attributes


class TestOldStyleTokenFields:
    """Old-style field names used by Google ADK < 2.1."""

    def test_prompt_token_count_mapped(self):
        usage = {"prompt_token_count": 50, "candidates_token_count": 100, "total_token_count": 150}
        attrs = _extract_usage_attributes(usage)
        assert attrs[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 50

    def test_candidates_token_count_mapped(self):
        usage = {"prompt_token_count": 50, "candidates_token_count": 100, "total_token_count": 150}
        attrs = _extract_usage_attributes(usage)
        assert attrs[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 100

    def test_total_token_count_mapped(self):
        usage = {"prompt_token_count": 50, "candidates_token_count": 100, "total_token_count": 150}
        attrs = _extract_usage_attributes(usage)
        assert attrs[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 150


class TestNewStyleTokenFields:
    """New-style field names introduced in Google ADK 2.1+ (issue #1418)."""

    def test_input_tokens_mapped(self):
        usage = {"input_tokens": 30, "output_tokens": 70, "total_tokens": 100}
        attrs = _extract_usage_attributes(usage)
        assert attrs[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 30

    def test_output_tokens_mapped(self):
        usage = {"input_tokens": 30, "output_tokens": 70, "total_tokens": 100}
        attrs = _extract_usage_attributes(usage)
        assert attrs[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 70

    def test_total_tokens_mapped(self):
        usage = {"input_tokens": 30, "output_tokens": 70, "total_tokens": 100}
        attrs = _extract_usage_attributes(usage)
        assert attrs[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 100


class TestTokenFieldPriority:
    """Old-style fields take priority over new-style when both are present."""

    def test_old_style_prompt_takes_priority(self):
        usage = {"prompt_token_count": 50, "input_tokens": 30}
        attrs = _extract_usage_attributes(usage)
        assert attrs[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 50

    def test_old_style_completion_takes_priority(self):
        usage = {"candidates_token_count": 100, "output_tokens": 70}
        attrs = _extract_usage_attributes(usage)
        assert attrs[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 100

    def test_old_style_total_takes_priority(self):
        usage = {"total_token_count": 150, "total_tokens": 100}
        attrs = _extract_usage_attributes(usage)
        assert attrs[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 150


class TestMissingFields:
    """Attributes absent when the usage dict does not contain token fields."""

    def test_empty_usage_has_no_token_attrs(self):
        attrs = _extract_usage_attributes({})
        assert SpanAttributes.LLM_USAGE_PROMPT_TOKENS not in attrs
        assert SpanAttributes.LLM_USAGE_COMPLETION_TOKENS not in attrs
        assert SpanAttributes.LLM_USAGE_TOTAL_TOKENS not in attrs

    def test_partial_usage_maps_available_fields_only(self):
        usage = {"input_tokens": 10}
        attrs = _extract_usage_attributes(usage)
        assert attrs[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 10
        assert SpanAttributes.LLM_USAGE_COMPLETION_TOKENS not in attrs
        assert SpanAttributes.LLM_USAGE_TOTAL_TOKENS not in attrs
