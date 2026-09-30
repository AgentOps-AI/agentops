import json
from unittest.mock import MagicMock
import pytest

from agentops.instrumentation.agentic.google_adk.patch import _extract_llm_attributes
from agentops.instrumentation.providers.google_genai.attributes.model import (
    _set_response_attributes,
)
from agentops.semconv import SpanAttributes


class TestGoogleTokenUsageExtraction:
    """Test suite verifying token usage normalization across Google ADK and GenAI."""

    def test_extract_llm_attributes_with_adk_token_names(self):
        """Verify _extract_llm_attributes correctly normalizes input_tokens and output_tokens from ADK."""
        llm_request_dict = {"model": "gemini-2.5-flash-lite"}
        llm_response = {
            "model": "gemini-2.5-flash-lite",
            "usage_metadata": {
                "input_tokens": 142,
                "output_tokens": 58,
            },
        }

        attrs = _extract_llm_attributes(llm_request_dict, json.dumps(llm_response))

        assert attrs[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 142
        assert attrs[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 58
        assert attrs[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 200

    def test_extract_llm_attributes_with_standard_gemini_token_counts(self):
        """Verify _extract_llm_attributes handles prompt_token_count and candidates_token_count."""
        llm_request_dict = {"model": "gemini-2.5-pro"}
        llm_response = {
            "model": "gemini-2.5-pro",
            "usage_metadata": {
                "prompt_token_count": 500,
                "candidates_token_count": 120,
                "total_token_count": 620,
            },
        }

        attrs = _extract_llm_attributes(llm_request_dict, json.dumps(llm_response))

        assert attrs[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 500
        assert attrs[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 120
        assert attrs[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 620

    def test_set_response_attributes_dict(self):
        """Verify _set_response_attributes with dictionary usage metadata."""
        attributes = {}
        response = MagicMock()
        response.model = "gemini-2.5-flash"
        response.usage_metadata = {
            "input_token_count": 350,
            "output_token_count": 80,
        }
        del response.text
        del response.candidates

        _set_response_attributes(attributes, response)

        assert attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 350
        assert attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 80
        assert attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 430

    def test_set_response_attributes_object(self):
        """Verify _set_response_attributes with object usage metadata."""
        attributes = {}
        response = MagicMock()
        response.model = "gemini-2.5-flash"
        usage_obj = MagicMock(spec=["prompt_token_count", "candidates_token_count", "total_token_count"])
        usage_obj.prompt_token_count = 210
        usage_obj.candidates_token_count = 95
        usage_obj.total_token_count = 305
        response.usage_metadata = usage_obj
        del response.text
        del response.candidates

        _set_response_attributes(attributes, response)

        assert attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] == 210
        assert attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] == 95
        assert attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] == 305
